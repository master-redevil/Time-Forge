import sys
import keyboard
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtCore import QObject, Signal, Slot, Qt

import database
from tracker import TrackerDaemon
from ui.settings import SettingsWindow
from ui.dashboard import DashboardWindow

class AppController(QObject):
    show_dashboard_sig = Signal()

    def __init__(self):
        super().__init__()
        database.init_db()

        self.settings_window = SettingsWindow()
        self.dashboard_window = DashboardWindow()
        
        self.dashboard_window.btn_settings.clicked.connect(self.show_settings)
        self.settings_window.apps_changed.connect(self.dashboard_window.refresh)

        # Start tracking daemon
        self.tracker = TrackerDaemon(poll_interval=5)
        self.tracker.updated.connect(self.dashboard_window.refresh)
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

    @Slot()
    def show_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def quit_app(self):
        self.tracker.stop()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep running in tray
    
    
    
    controller = AppController()
    sys.exit(app.exec())
