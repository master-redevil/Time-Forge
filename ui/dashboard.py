from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QListWidget, QListWidgetItem, QFileIconProvider, QStyle,
    QFrame, QGridLayout, QScrollArea, QGroupBox
)
from PySide6.QtCore import Qt, QTimer, QFileInfo, Signal, QSize, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QPainter, QColor, QFont, QIcon, QPixmap, QBrush, QPainterPath
from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries, QBarSeries, QStackedBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
)
import database
import os
import psutil
import ctypes
from ctypes import wintypes
import datetime

def get_foreground_app():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    try:
        proc = psutil.Process(pid.value)
        return proc.name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{secs:02}"
    return f"{minutes:02}:{secs:02}"

class SidebarButton(QPushButton):
    def __init__(self, text, icon_name=None):
        super().__init__(text)
        self.setCheckable(True)
        self.setFixedHeight(45)
        self.setCursor(Qt.PointingHandCursor)
        if icon_name:
            # Placeholder for icons, using standard icons for now
            pass

class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setObjectName("Sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(10)

        self.logo = QLabel("TIME FORGE")
        self.logo.setObjectName("SidebarLogo")
        self.logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo)
        layout.addSpacing(20)

        self.btn_home = SidebarButton(" Dashboard")
        self.btn_stats = SidebarButton(" Statistics")
        self.btn_apps = SidebarButton(" Tracked Apps")
        self.btn_settings = SidebarButton(" Settings")

        self.buttons = [self.btn_home, self.btn_stats, self.btn_apps, self.btn_settings]
        for btn in self.buttons:
            layout.addWidget(btn)
        
        layout.addStretch()
        
class StatusCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusCard")
        self.setFixedHeight(75) # Increased height for larger text
        self.setStyleSheet("""
            QFrame#StatusCard {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
            }
            QLabel#StatusTitle {
                color: #a6e3a1;
                font-size: 15px;
                font-weight: bold;
            }
            QLabel#StatusSub {
                color: #7f849c;
                font-size: 13px;
            }
        """)
        
        layout = QGridLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(2)

        self.dot = QFrame()
        self.dot.setFixedSize(10, 10)
        self.dot.setStyleSheet("background-color: #a6e3a1; border-radius: 5px;")
        
        self.title = QLabel("Tracking Active")
        self.title.setObjectName("StatusTitle")
        
        self.subtitle = QLabel("Started at --:--")
        self.subtitle.setObjectName("StatusSub")
        
        layout.addWidget(self.dot, 0, 0)
        layout.addWidget(self.title, 0, 1)
        layout.addWidget(self.subtitle, 1, 1)
        layout.setColumnStretch(1, 1)

    def set_active(self, is_active, start_time="--:--"):
        if is_active:
            self.dot.setStyleSheet("background-color: #a6e3a1; border-radius: 5px;")
            self.title.setText("Tracking Active")
            self.title.setStyleSheet("color: #a6e3a1; font-weight: bold;")
            self.subtitle.setText(f"Started at {start_time}")
        else:
            self.dot.setStyleSheet("background-color: #f9e2af; border-radius: 5px;")
            self.title.setText("Tracking Paused")
            self.title.setStyleSheet("color: #f9e2af; font-weight: bold;")
            self.subtitle.setText("System Idle")

class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setObjectName("Sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(10)

        self.logo = QLabel("TIME FORGE")
        self.logo.setObjectName("SidebarLogo")
        self.logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo)
        layout.addSpacing(20)

        self.btn_home = SidebarButton(" Dashboard")
        self.btn_stats = SidebarButton(" Statistics")
        self.btn_apps = SidebarButton(" Tracked Apps")
        self.btn_settings = SidebarButton(" Settings")

        self.buttons = [self.btn_home, self.btn_stats, self.btn_apps, self.btn_settings]
        for btn in self.buttons:
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # New Status Card
        self.status_card = StatusCard()
        layout.addWidget(self.status_card)

    def set_active_button(self, index):
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)

class SummaryCard(QFrame):
    def __init__(self, title, value, color="#89b4fa"):
        super().__init__()
        self.setObjectName("SummaryCard")
        self.setStyleSheet(f"""
            QFrame#SummaryCard {{
                background-color: #313244;
                border-radius: 12px;
                padding: 15px;
            }}
            QLabel#CardTitle {{
                color: #bac2de;
                font-size: 12px;
                text-transform: uppercase;
                font-weight: bold;
            }}
            QLabel#CardValue {{
                color: {color};
                font-size: 24px;
                font-weight: bold;
            }}
        """)
        layout = QVBoxLayout(self)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("CardTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("CardValue")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

class SummaryView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("Overview")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #f5e0dc;")
        layout.addWidget(header)

        # Cards
        cards_layout = QHBoxLayout()
        self.total_usage_card = SummaryCard("Total Usage", "00:00:00")
        self.top_app_card = SummaryCard("Most Used App", "None", "#f38ba8")
        self.session_card = SummaryCard("Current Session", "00:00:00", "#fab387")
        cards_layout.addWidget(self.total_usage_card)
        cards_layout.addWidget(self.top_app_card)
        cards_layout.addWidget(self.session_card)
        layout.addLayout(cards_layout)

        # Mini Chart Placeholder or Recent Activity
        layout.addSpacing(10)
        recent_label = QLabel("Recent Activity Tracking")
        recent_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #cdd6f4; margin-bottom: 5px;")
        layout.addWidget(recent_label)
        
        self.recent_list = QListWidget()
        self.recent_list.setObjectName("RecentList")
        layout.addWidget(self.recent_list, 1) # Give it stretch

class SettingsView(QWidget):
    apps_changed = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel("Application Settings")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #f5e0dc; margin-bottom: 10px;")
        layout.addWidget(header)

        lists_layout = QHBoxLayout()
        
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

        lists_layout.addWidget(running_group)
        lists_layout.addWidget(tracked_group)
        layout.addLayout(lists_layout)

    def clean_name(self, name):
        if name.lower().endswith('.exe'):
            return name[:-4].title()
        return name.title()

    def load_tracked_apps(self):
        self.tracked_list.clear()
        apps = database.get_tracked_apps()
        for app in apps:
            item = QListWidgetItem(self.clean_name(app))
            item.setData(Qt.UserRole, app)
            self.tracked_list.addItem(item)

    def load_running_processes(self):
        self.running_list.clear()
        running = set()
        self.running_exes = {}
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                name = proc.info.get('name')
                exe = proc.info.get('exe')
                if name:
                    name_lower = name.lower()
                    running.add(name_lower)
                    if exe and name_lower not in self.running_exes:
                        self.running_exes[name_lower] = exe
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        tracked = set(database.get_tracked_apps())
        available = sorted(list(running - tracked))
        for app in available:
            item = QListWidgetItem(self.clean_name(app))
            item.setData(Qt.UserRole, app)
            self.running_list.addItem(item)

    def add_app(self):
        item = self.running_list.currentItem()
        if not item: return
        app_name = item.data(Qt.UserRole)
        exe_path = getattr(self, 'running_exes', {}).get(app_name)
        if database.add_tracked_app(app_name, exe_path):
            self.load_tracked_apps()
            self.load_running_processes()
            self.apps_changed.emit()

    def remove_app(self):
        item = self.tracked_list.currentItem()
        if not item: return
        app_name = item.data(Qt.UserRole)
        database.remove_tracked_app(app_name)
        self.load_tracked_apps()
        self.load_running_processes()
        self.apps_changed.emit()

class DashboardWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(900, 600)
        
        self.setStyleSheet("""
            QWidget#MainContainer {
                background-color: #1e1e2e;
                border-radius: 15px;
                border: 1px solid #45475a;
            }
            Sidebar {
                background-color: #181825;
                border-top-left-radius: 15px;
                border-bottom-left-radius: 15px;
                border-right: 1px solid #313244;
            }
            QLabel#SidebarLogo {
                color: #89b4fa;
                font-size: 18px;
                font-weight: bold;
                letter-spacing: 2px;
            }
            SidebarButton {
                background-color: transparent;
                color: #bac2de;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding-left: 15px;
                font-weight: 500;
                font-size: 14px;
                margin-right: 10px;
            }
            SidebarButton:hover {
                background-color: rgba(69, 71, 90, 100);
                color: #cdd6f4;
            }
            SidebarButton:checked {
                background-color: rgba(137, 180, 250, 40);
                color: #89b4fa;
                border-left: 3px solid #89b4fa;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
            }
            QListWidget {
                background-color: #181825;
                border-radius: 8px;
                border: 1px solid #313244;
                color: #cdd6f4;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #313244;
                border-radius: 5px;
            }
            QListWidget::item:hover {
                background-color: #313244;
            }
            QListWidget::item:selected {
                background-color: rgba(137, 180, 250, 30);
                color: #89b4fa;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #585b70;
            }
            QPushButton:pressed {
                background-color: #1e1e2e;
            }
            QGroupBox {
                border: 1px solid #45475a;
                border-radius: 8px;
                margin-top: 15px;
                color: #bac2de;
                font-weight: bold;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        self.app_start_time = datetime.datetime.now().strftime("%I:%M %p")
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.container = QWidget()
        self.container.setObjectName("MainContainer")
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        container_layout.addWidget(self.sidebar)

        # Content Area
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # Custom Title Bar for Content Area
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(0, 0, 10, 0)
        title_bar_layout.addStretch()
        
        window_btn_style = """
            QPushButton {
                background-color: transparent;
                color: #7f849c;
                border: none;
                border-radius: 15px;
                font-size: 16px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(127, 132, 156, 30);
                color: #cdd6f4;
            }
        """

        self.btn_min = QPushButton("—")
        self.btn_min.setFixedSize(30, 30)
        self.btn_min.setCursor(Qt.PointingHandCursor)
        self.btn_min.setStyleSheet(window_btn_style)
        self.btn_min.clicked.connect(self.showMinimized)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(window_btn_style + "QPushButton:hover { background-color: #f38ba8; color: #11111b; }")
        self.btn_close.clicked.connect(self.hide)
        
        title_bar_layout.addWidget(self.btn_min)
        title_bar_layout.addWidget(self.btn_close)
        self.content_layout.addWidget(title_bar)

        # Stacked Widget
        self.stacked_widget = QStackedWidget()
        
        self.summary_view = SummaryView()
        self.stats_view = QWidget() # Placeholder for stats view
        self.apps_view = QListWidget()
        self.settings_view = SettingsView()

        self.stacked_widget.addWidget(self.summary_view)
        self.stacked_widget.addWidget(self.stats_view)
        self.stacked_widget.addWidget(self.apps_view)
        self.stacked_widget.addWidget(self.settings_view)

        self.content_layout.addWidget(self.stacked_widget)
        container_layout.addWidget(content_widget)
        
        main_layout.addWidget(self.container)

        # Connect Sidebar Buttons
        self.sidebar.btn_home.clicked.connect(lambda: self.switch_view(0))
        self.sidebar.btn_stats.clicked.connect(lambda: self.switch_view(1))
        self.sidebar.btn_apps.clicked.connect(lambda: self.switch_view(2))
        self.sidebar.btn_settings.clicked.connect(lambda: self.switch_view(3))
        
        # Initialize Stats View Components
        self.setup_stats_view()

        # Initial View
        self.switch_view(0)

    def setup_stats_view(self):
        stats_layout = QVBoxLayout(self.stats_view)
        stats_layout.setContentsMargins(20, 0, 20, 20)
        
        header = QLabel("Usage Statistics")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #f5e0dc; margin-bottom: 10px;")
        stats_layout.addWidget(header)

        # Charts Stack
        self.charts_stack = QStackedWidget()
        
        self.bar_chart = QChart()
        self.bar_chart.setBackgroundBrush(QColor(0, 0, 0, 0))
        self.bar_view = QChartView(self.bar_chart)
        self.bar_view.setRenderHint(QPainter.Antialiasing)
        
        self.pie_chart = QChart()
        self.pie_chart.setBackgroundBrush(QColor(0, 0, 0, 0))
        self.pie_view = QChartView(self.pie_chart)
        self.pie_view.setRenderHint(QPainter.Antialiasing)
        
        self.charts_stack.addWidget(self.bar_view)
        self.charts_stack.addWidget(self.pie_view)
        
        stats_layout.addWidget(self.charts_stack)
        
        # Toggle for charts
        toggle_layout = QHBoxLayout()
        self.btn_bar = QPushButton("Bar Chart")
        self.btn_pie = QPushButton("Pie Chart")
        self.btn_bar.clicked.connect(lambda: self.charts_stack.setCurrentIndex(0))
        self.btn_pie.clicked.connect(lambda: self.charts_stack.setCurrentIndex(1))
        toggle_layout.addStretch()
        toggle_layout.addWidget(self.btn_bar)
        toggle_layout.addWidget(self.btn_pie)
        stats_layout.addLayout(toggle_layout)

    def switch_view(self, index):
        self.stacked_widget.setCurrentIndex(index)
        self.sidebar.set_active_button(index)
        if index == 3:
            self.settings_view.load_tracked_apps()
            self.settings_view.load_running_processes()
        self.load_data()

    def load_data(self):
        data = database.get_today_usage()
        tracked_apps = set(database.get_tracked_apps())
        filtered_data = {k: v for k, v in data.items() if k in tracked_apps}
        sorted_data = sorted(filtered_data.items(), key=lambda x: x[1], reverse=True)
        
        active_sessions = database.get_active_sessions()
        app_paths = database.get_app_paths()
        icon_provider = QFileIconProvider()

        def clean_name(name):
            if name.lower().endswith('.exe'):
                return name[:-4].title()
            return name.title()

        cleaned_data = [(app, clean_name(app), seconds) for app, seconds in sorted_data]

        # Update Summary View
        total_device_seconds = database.get_today_device_activity()
        self.summary_view.total_usage_card.value_label.setText(format_time(total_device_seconds))
        
        if cleaned_data:
            self.summary_view.top_app_card.value_label.setText(cleaned_data[0][1])
            
            self.summary_view.recent_list.clear()
            self.summary_view.recent_list.setIconSize(QSize(24, 24))
            for app, friendly_name, seconds in cleaned_data[:5]:
                if app in active_sessions:
                    item_text = f"{friendly_name} | {format_time(seconds)} (Session: {format_time(active_sessions[app])})"
                else:
                    item_text = f"{friendly_name} | {format_time(seconds)}"
                
                item = QListWidgetItem(item_text)
                exe_path = app_paths.get(app)
                if exe_path and os.path.exists(exe_path):
                    item.setIcon(icon_provider.icon(QFileInfo(exe_path)))
                self.summary_view.recent_list.addItem(item)
        else:
            self.summary_view.top_app_card.value_label.setText("None")
            self.summary_view.recent_list.clear()
            self.summary_view.recent_list.addItem("No data recorded yet.")

        # Update Session Card (Focused App only)
        focused = get_foreground_app()
        session_time = active_sessions.get(focused, 0)
        self.summary_view.session_card.value_label.setText(format_time(session_time))

        # Update Apps View (List Widget)
        self.apps_view.clear()
        self.apps_view.setIconSize(QSize(32, 32))
        for app, friendly_name, seconds in cleaned_data:
            if app in active_sessions:
                item_text = f"{friendly_name} | Total: {format_time(seconds)} | Session: {format_time(active_sessions[app])}"
            else:
                item_text = f"{friendly_name} | Total: {format_time(seconds)}"
            item = QListWidgetItem(item_text)
            exe_path = app_paths.get(app)
            if exe_path and os.path.exists(exe_path):
                item.setIcon(icon_provider.icon(QFileInfo(exe_path)))
            self.apps_view.addItem(item)

        # Update Charts (reuse existing logic but simplified for new theme)
        self.update_charts(cleaned_data, app_paths, icon_provider)

    def update_charts(self, cleaned_data, app_paths, icon_provider):
        # Bar Chart
        self.bar_chart.removeAllSeries()
        for ax in self.bar_chart.axes(): self.bar_chart.removeAxis(ax)
        
        bar_series = QStackedBarSeries()
        colors = ["#89b4fa", "#f38ba8", "#a6e3a1", "#f9e2af", "#cba6f7", "#89dceb", "#fab387"]
        
        categories = [friendly_name for app, friendly_name, seconds in cleaned_data[:7]]
        for i, (app, friendly_name, seconds) in enumerate(cleaned_data[:7]):
            bar_set = QBarSet(friendly_name)
            for _ in range(i): bar_set.append(0)
            bar_set.append(seconds / 60)
            for _ in range(len(categories) - i - 1): bar_set.append(0)
            bar_set.setColor(QColor(colors[i % len(colors)]))
            bar_series.append(bar_set)
            
        self.bar_chart.addSeries(bar_series)
        self.bar_chart.legend().setLabelColor(QColor("#cdd6f4"))
        
        # Pie Chart
        self.pie_chart.removeAllSeries()
        pie_series = QPieSeries()
        for i, (app, friendly_name, seconds) in enumerate(cleaned_data[:5]):
            slice = pie_series.append(friendly_name, seconds)
            slice.setBrush(QColor(colors[i % len(colors)]))
            slice.setLabelVisible(True)
            slice.setLabelColor(QColor("#cdd6f4"))
        self.pie_chart.addSeries(pie_series)
        self.pie_chart.legend().setLabelColor(QColor("#cdd6f4"))

    def refresh(self):
        self.load_data()

    def update_idle_status(self, is_idle):
        self.sidebar.status_card.set_active(not is_idle, self.app_start_time)
