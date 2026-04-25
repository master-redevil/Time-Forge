from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QPushButton, QMessageBox, QGroupBox
)
import psutil
import database

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Time Forge - Settings")
        self.resize(600, 500)
        
        # Apply dark mode style for premium look
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Segoe UI', Inter, sans-serif;
            }
            QGroupBox {
                border: 1px solid #45475a;
                border-radius: 6px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QListWidget {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #89b4fa;
                color: #11111b;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #11111b;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton:pressed {
                background-color: #74c7ec;
            }
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)

        # Left column: Running Processes
        running_group = QGroupBox("Running Processes")
        running_layout = QVBoxLayout(running_group)
        self.running_list = QListWidget()
        self.btn_refresh = QPushButton("Refresh List")
        self.btn_refresh.clicked.connect(self.load_running_processes)
        self.btn_add = QPushButton("Track Selected ->")
        self.btn_add.clicked.connect(self.add_app)
        
        running_layout.addWidget(self.running_list)
        running_layout.addWidget(self.btn_refresh)
        running_layout.addWidget(self.btn_add)

        # Right column: Tracked Apps
        tracked_group = QGroupBox("Tracked Applications")
        tracked_layout = QVBoxLayout(tracked_group)
        self.tracked_list = QListWidget()
        self.btn_remove = QPushButton("<- Stop Tracking")
        self.btn_remove.clicked.connect(self.remove_app)
        
        tracked_layout.addWidget(self.tracked_list)
        tracked_layout.addWidget(self.btn_remove)

        layout.addWidget(running_group)
        layout.addWidget(tracked_group)

        self.load_tracked_apps()
        self.load_running_processes()

    def load_tracked_apps(self):
        self.tracked_list.clear()
        apps = database.get_tracked_apps()
        for app in apps:
            self.tracked_list.addItem(app)

    def load_running_processes(self):
        self.running_list.clear()
        running = set()
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name']
                if name:
                    running.add(name.lower())
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        tracked = set(database.get_tracked_apps())
        # Filter out already tracked apps
        available = sorted(list(running - tracked))
        for app in available:
            self.running_list.addItem(app)

    def add_app(self):
        item = self.running_list.currentItem()
        if not item:
            return
        app_name = item.text()
        if database.add_tracked_app(app_name):
            self.load_tracked_apps()
            self.load_running_processes()

    def remove_app(self):
        item = self.tracked_list.currentItem()
        if not item:
            return
        app_name = item.text()
        database.remove_tracked_app(app_name)
        self.load_tracked_apps()
        self.load_running_processes()
