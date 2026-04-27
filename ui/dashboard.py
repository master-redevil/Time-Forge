from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QListWidget, QListWidgetItem, QFileIconProvider, QStyle
)
from PySide6.QtCore import Qt, QTimer, QFileInfo, Signal, QSize
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries, QBarSeries, QStackedBarSeries, QBarSet, QBarCategoryAxis, QValueAxis, QLegendMarker
)
from PySide6.QtGui import QBrush
import database
import os

def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"

class DashboardWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Game Bar style overlay
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(700, 450)
        
        self.setStyleSheet("""
            QWidget#MainContainer {
                background-color: rgba(30, 30, 46, 230);
                border-radius: 10px;
                border: 1px solid #45475a;
            }
            QLabel {
                color: #cdd6f4;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel#Title {
                font-size: 18px;
                font-weight: bold;
                color: #89b4fa;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 5px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
            QPushButton:checked {
                background-color: #89b4fa;
                color: #11111b;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                color: #cdd6f4;
                font-size: 14px;
            }
            QListWidget::item {
                border-bottom: 1px solid #313244;
                margin: 4px;
            }
        """)

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.container = QWidget()
        self.container.setObjectName("MainContainer")
        container_layout = QVBoxLayout(self.container)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Time Forge Dashboard")
        title.setObjectName("Title")
        
        # View Toggles
        self.btn_text = QPushButton("Plain Text")
        self.btn_text.setCheckable(True)
        self.btn_text.setChecked(True)
        self.btn_bar = QPushButton("Bar Chart")
        self.btn_bar.setCheckable(True)
        self.btn_pie = QPushButton("Pie Chart")
        self.btn_pie.setCheckable(True)
        
        self.btn_settings = QPushButton("⚙ Settings")
        
        self.btn_min = QPushButton()
        self.btn_min.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMinButton))
        self.btn_min.setFixedSize(30, 30)
        self.btn_min.clicked.connect(self.showMinimized)

        self.btn_max = QPushButton()
        self.btn_max.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.btn_max.setFixedSize(30, 30)
        self.btn_max.clicked.connect(self.toggle_maximize)
        
        self.btn_close = QPushButton()
        self.btn_close.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.clicked.connect(self.hide)

        # Exclusive toggle logic
        self.btn_text.clicked.connect(lambda: self.switch_view(0))
        self.btn_bar.clicked.connect(lambda: self.switch_view(1))
        self.btn_pie.clicked.connect(lambda: self.switch_view(2))

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_text)
        header_layout.addWidget(self.btn_bar)
        header_layout.addWidget(self.btn_pie)
        header_layout.addWidget(self.btn_settings)
        header_layout.addWidget(self.btn_min)
        header_layout.addWidget(self.btn_max)
        header_layout.addWidget(self.btn_close)

        # Stacked Widget for different views
        self.stacked_widget = QStackedWidget()
        
        # 1. Plain Text View
        self.text_view = QListWidget()
        
        # 2. Bar Chart View
        self.bar_chart = QChart()
        self.bar_chart.setBackgroundBrush(QColor(0, 0, 0, 0))
        self.bar_view = QChartView(self.bar_chart)
        self.bar_view.setRenderHint(QPainter.Antialiasing)
        self.bar_view.setStyleSheet("background: transparent;")
        
        # 3. Pie Chart View
        self.pie_chart = QChart()
        self.pie_chart.setBackgroundBrush(QColor(0, 0, 0, 0))
        self.pie_chart.legend().setLabelBrush(QColor("#cdd6f4"))
        self.pie_view = QChartView(self.pie_chart)
        self.pie_view.setRenderHint(QPainter.Antialiasing)
        self.pie_view.setStyleSheet("background: transparent;")

        self.stacked_widget.addWidget(self.text_view)
        self.stacked_widget.addWidget(self.bar_view)
        self.stacked_widget.addWidget(self.pie_view)

        container_layout.addLayout(header_layout)
        container_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(self.container)

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def switch_view(self, index):
        self.btn_text.setChecked(index == 0)
        self.btn_bar.setChecked(index == 1)
        self.btn_pie.setChecked(index == 2)
        self.stacked_widget.setCurrentIndex(index)
        self.load_data()

    def load_data(self):
        data = database.get_today_usage()
        tracked_apps = set(database.get_tracked_apps())
        # Filter only currently tracked apps
        filtered_data = {k: v for k, v in data.items() if k in tracked_apps}
        # Sort by duration descending
        sorted_data = sorted(filtered_data.items(), key=lambda x: x[1], reverse=True)
        
        if not sorted_data:
            self.text_view.clear()
            self.text_view.addItem("No usage data recorded for today yet.")
            return

        app_paths = database.get_app_paths()
        icon_provider = QFileIconProvider()
        
        active_sessions = database.get_active_sessions()

        def clean_name(name):
            if name.lower().endswith('.exe'):
                return name[:-4].title()
            return name.title()

        cleaned_data = [(app, clean_name(app), seconds) for app, seconds in sorted_data]

        # Update Text View
        self.text_view.clear()
        self.text_view.setIconSize(QSize(32, 32))
        for app, friendly_name, seconds in cleaned_data:
            if app in active_sessions:
                session_seconds = active_sessions[app]
                item_text = f"{friendly_name} | Total: {format_time(seconds)} | Session: {format_time(session_seconds)}"
            else:
                item_text = f"{friendly_name} | Total: {format_time(seconds)}"
            item = QListWidgetItem(item_text)
            
            exe_path = app_paths.get(app)
            if exe_path and os.path.exists(exe_path):
                icon = icon_provider.icon(QFileInfo(exe_path))
                item.setIcon(icon)
                
            self.text_view.addItem(item)

        # Update Bar Chart
        self.bar_chart.removeAllSeries()
        for ax in self.bar_chart.axes():
            self.bar_chart.removeAxis(ax)
            
        bar_series = QStackedBarSeries()
        self.bar_chart.legend().setVisible(True)
        self.bar_chart.legend().setLabelColor(QColor("#cdd6f4"))
        
        categories = [friendly_name for app, friendly_name, seconds in cleaned_data[:10]]
        colors = ["#89b4fa", "#f38ba8", "#a6e3a1", "#f9e2af", "#cba6f7", "#89dceb", "#fab387", "#eba0ac", "#94e2d5", "#f5c2e7"]
        
        for i, (app, friendly_name, seconds) in enumerate(cleaned_data[:10]): # top 10
            bar_set = QBarSet(friendly_name)
            # Pad with zeroes so each bar is in its own category column
            for _ in range(i):
                bar_set.append(0)
            bar_set.append(seconds / 60) # in minutes
            for _ in range(len(categories) - i - 1):
                bar_set.append(0)
            
            bar_set.setColor(QColor(colors[i % len(colors)]))
            bar_series.append(bar_set)
            
        self.bar_chart.addSeries(bar_series)
        
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsBrush(QColor("#cdd6f4"))
        self.bar_chart.addAxis(axis_x, Qt.AlignBottom)
        bar_series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setTitleText("Minutes")
        axis_y.setLabelsBrush(QColor("#cdd6f4"))
        axis_y.setTitleBrush(QColor("#cdd6f4"))
        self.bar_chart.addAxis(axis_y, Qt.AlignLeft)
        bar_series.attachAxis(axis_y)

        # Set Icon Brushes for Bar Chart Legend
        bar_markers = self.bar_chart.legend().markers()
        for i, (app, friendly_name, seconds) in enumerate(cleaned_data[:10]):
            exe_path = app_paths.get(app)
            if exe_path and os.path.exists(exe_path):
                icon = icon_provider.icon(QFileInfo(exe_path))
                if not icon.isNull() and i < len(bar_markers):
                    bar_markers[i].setBrush(QBrush(icon.pixmap(16, 16)))

        # Update Pie Chart
        self.pie_chart.removeAllSeries()
        pie_series = QPieSeries()
        colors = ["#89b4fa", "#f38ba8", "#a6e3a1", "#f9e2af", "#cba6f7"]
        for i, (app, friendly_name, seconds) in enumerate(cleaned_data[:5]): # Top 5 for pie
            slice = pie_series.append(friendly_name, seconds)
            slice.setBrush(QColor(colors[i % len(colors)]))
            slice.setLabelVisible(True)
            slice.setLabelColor(QColor("#cdd6f4"))
            
        self.pie_chart.addSeries(pie_series)

        # Set Icon Brushes for Pie Chart Legend
        pie_markers = self.pie_chart.legend().markers()
        for i, (app, friendly_name, seconds) in enumerate(cleaned_data[:5]):
            exe_path = app_paths.get(app)
            if exe_path and os.path.exists(exe_path):
                icon = icon_provider.icon(QFileInfo(exe_path))
                if not icon.isNull() and i < len(pie_markers):
                    pie_markers[i].setBrush(QBrush(icon.pixmap(16, 16)))

    def refresh(self):
        self.load_data()
