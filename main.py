import sys
import keyboard
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtCore import QObject, Signal, Slot, Qt

import database
from tracker import TrackerDaemon
from ui.dashboard import DashboardWindow

class AppController(QObject):
    show_dashboard_sig = Signal()

    def __init__(self):
        super().__init__()
        database.init_db()

        self.dashboard_window = DashboardWindow()
        
        # Connect integrated settings signal
        self.dashboard_window.settings_view.apps_changed.connect(self.dashboard_window.refresh)

        # Start tracking daemon
        self.tracker = TrackerDaemon(poll_interval=1)
        self.tracker.updated.connect(self.dashboard_window.refresh)
        self.tracker.idle_status_changed.connect(self.dashboard_window.update_idle_status)
        self.tracker.start()

        self.setup_tray()
        
        # Connect signal for thread-safe UI update from hotkey
        self.show_dashboard_sig.connect(self.toggle_dashboard)
        keyboard.add_hotkey('ctrl+shift+t', self.show_dashboard_sig.emit)

    def setup_tray(self):
        # Create a simple icon programmatically
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setBrush(QColor("#89b4fa"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 56, 56)
        painter.end()
        icon = QIcon(pixmap)

        self.tray_icon = QSystemTrayIcon(icon)
        self.tray_icon.setToolTip("Time Forge (Ctrl+Shift+T)")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
            }
            QMenu::item:selected {
                background-color: #313244;
            }
        """)
        
        action_show = menu.addAction("Show Dashboard")
        action_show.triggered.connect(self.toggle_dashboard)
        
        menu.addSeparator()
        
        action_quit = menu.addAction("Quit")
        action_quit.triggered.connect(self.quit_app)
        self.tray_icon.setContextMenu(menu)

        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger or reason == QSystemTrayIcon.DoubleClick:
            self.toggle_dashboard()

    @Slot()
    def toggle_dashboard(self):
        if self.dashboard_window.isVisible():
            self.dashboard_window.hide()
        else:
            self.dashboard_window.refresh()
            self.dashboard_window.show()
            self.dashboard_window.activateWindow()

    def quit_app(self):
        self.tracker.stop()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep running in tray
    
    controller = AppController()
    sys.exit(app.exec())
