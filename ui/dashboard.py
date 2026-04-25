from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
)
import database

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
                padding: 8px;
                border-bottom: 1px solid #313244;
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
        
        self.btn_close = QPushButton("X")
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
        header_layout.addWidget(self.btn_close)

        # Stacked Widget for different views
        self.stacked_widget = QStackedWidget()
        
        # 1. Plain Text View
        self.text_view = QListWidget()
        
        # 2. Bar Chart View
        self.bar_chart = QChart()
        self.bar_chart.setBackgroundBrush(QColor(0, 0, 0, 0))
        self.bar_chart.legend().hide()
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

    def switch_view(self, index):
        self.btn_text.setChecked(index == 0)
        self.btn_bar.setChecked(index == 1)
        self.btn_pie.setChecked(index == 2)
        self.stacked_widget.setCurrentIndex(index)
        self.load_data()

    def load_data(self):
        data = database.get_today_usage()
        # Sort by duration descending
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
        
        if not sorted_data:
            self.text_view.clear()
            self.text_view.addItem("No usage data recorded for today yet.")
            return

        # Update Text View
        self.text_view.clear()
        for app, seconds in sorted_data:
            item_text = f"{app}: {format_time(seconds)}"
            self.text_view.addItem(item_text)

        # Update Bar Chart
        self.bar_chart.removeAllSeries()
        for ax in self.bar_chart.axes():
            self.bar_chart.removeAxis(ax)
            
        bar_series = QBarSeries()
        bar_set = QBarSet("Usage")
        bar_set.setColor(QColor("#89b4fa"))
        categories = []
        
        for app, seconds in sorted_data[:10]: # top 10
            bar_set.append(seconds / 60) # in minutes
            categories.append(app)
            
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

        # Update Pie Chart
        self.pie_chart.removeAllSeries()
        pie_series = QPieSeries()
        colors = ["#89b4fa", "#f38ba8", "#a6e3a1", "#f9e2af", "#cba6f7"]
        for i, (app, seconds) in enumerate(sorted_data[:5]): # Top 5 for pie
            slice = pie_series.append(app, seconds)
            slice.setBrush(QColor(colors[i % len(colors)]))
            slice.setLabelVisible(True)
            slice.setLabelColor(QColor("#cdd6f4"))
            
        self.pie_chart.addSeries(pie_series)

    def refresh(self):
        self.load_data()
