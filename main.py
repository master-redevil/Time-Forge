import sys
import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtCore import QObject, Signal, Slot, Qt, QAbstractNativeEventFilter

import database
from tracker import TrackerDaemon
from ui.dashboard import DashboardWindow
from config import config

# Setup logging
import logging
from logging.handlers import RotatingFileHandler
import os

log_dir = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'TimeForge')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'time_forge.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=3),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TimeForge")
logger.info("Application starting...")

class NativeHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, hotkey_id, signal):
        super().__init__()
        self.hotkey_id = hotkey_id
        self.signal = signal

    def nativeEventFilter(self, eventType, message):
        # P1.4: Listen for WM_HOTKEY message (0x0312)
        if eventType == "windows_generic_MSG":
            msg = wintypes.MSG.from_address(message.__int__())
            if msg.message == 0x0312: # WM_HOTKEY
                if msg.wParam == self.hotkey_id:
                    self.signal.emit()
                    return True, 0
        return False, 0

class AppController(QObject):
    show_dashboard_sig = Signal()

    def __init__(self):
        super().__init__()
        database.init_db()

        self.dashboard_window = DashboardWindow()
        
        # Connect integrated settings signal
        self.dashboard_window.settings_view.apps_changed.connect(self.dashboard_window.refresh)

        # Start tracking daemon
        self.tracker = TrackerDaemon(poll_interval=config.get("poll_interval", 1))
        self.tracker.updated.connect(self.dashboard_window.refresh)
        self.tracker.idle_status_changed.connect(self.dashboard_window.update_idle_status)
        self.tracker.error_occurred.connect(self.handle_tracker_error)
        self.tracker.start()

        self.setup_tray()
        
        # Connect signal for thread-safe UI update from hotkey
        self.show_dashboard_sig.connect(self.toggle_dashboard)
        
        # P1.4: Native Hotkey Registration
        self.HOTKEY_ID = 1
        self.hotkey_filter = NativeHotkeyFilter(self.HOTKEY_ID, self.show_dashboard_sig)
        QApplication.instance().installNativeEventFilter(self.hotkey_filter)
        
        # Parse hotkey from config (e.g. "Ctrl+Shift+T")
        # For now, we only support the default modifiers for simplicity
        MOD_CONTROL = 0x0002
        MOD_SHIFT = 0x0004
        VK_T = 0x54 # 'T' key
        
        if not ctypes.windll.user32.RegisterHotKey(None, self.HOTKEY_ID, MOD_CONTROL | MOD_SHIFT, VK_T):
            logger.warning(f"Could not register global hotkey {config.get('hotkey')}")

    def setup_tray(self):
        import os
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        icon = QIcon(logo_path) if os.path.exists(logo_path) else QIcon()
        
        QApplication.setWindowIcon(icon)
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

    @Slot(str)
    def handle_tracker_error(self, message):
        logger.error(f"Tracker reported error: {message}")
        self.dashboard_window.show_tracker_error(message)

    @Slot()
    def toggle_dashboard(self):
        if self.dashboard_window.isVisible():
            self.dashboard_window.hide()
        else:
            self.dashboard_window.show()
            self.dashboard_window.refresh(force=True)
            self.dashboard_window.activateWindow()

    def quit_app(self):
        # P1.4: Properly unregister hotkey to release system resource
        if hasattr(self, 'HOTKEY_ID'):
            ctypes.windll.user32.UnregisterHotKey(None, self.HOTKEY_ID)
        self.tracker.stop()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep running in tray
    
    controller = AppController()
    sys.exit(app.exec())
