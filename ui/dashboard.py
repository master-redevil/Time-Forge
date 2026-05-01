from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QListWidget, QListWidgetItem, QFileIconProvider, QStyle,
    QFrame, QGridLayout, QScrollArea, QGroupBox, QGraphicsDropShadowEffect, QGraphicsColorizeEffect,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QFileInfo, Signal, QSize, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QPainter, QColor, QFont, QIcon, QPixmap, QBrush, QPainterPath, QLinearGradient, QPen
from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries, QBarSeries, QStackedBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
)
import database
import os
import psutil
import ctypes
from ctypes import wintypes
import datetime
from PySide6.QtCore import Property

class WindowButton(QPushButton):
    def __init__(self, icon_type, hover_color, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type # 'min' or 'close'
        self.hover_color = QColor(hover_color)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.PointingHandCursor)
        
        # Hover animation properties
        self._bg_opacity = 0
        self.anim = QPropertyAnimation(self, b"bg_opacity")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)

    @Property(float)
    def bg_opacity(self): return self._bg_opacity
    @bg_opacity.setter
    def bg_opacity(self, v):
        self._bg_opacity = v
        self.update()

    def enterEvent(self, event):
        self.anim.setDirection(QPropertyAnimation.Forward)
        if self.anim.state() == QPropertyAnimation.Stopped:
            self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.setDirection(QPropertyAnimation.Backward)
        if self.anim.state() == QPropertyAnimation.Stopped:
            self.anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        if self._bg_opacity > 0:
            color = QColor(self.hover_color)
            color.setAlphaF(self._bg_opacity * 0.15)
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(self.rect(), 16, 16)

        # Draw Icon
        icon_color = QColor("#64748B")
        if self._bg_opacity > 0:
            # Blend towards the hover color
            icon_color = self.hover_color
            
        painter.setPen(QPen(icon_color, 2, Qt.SolidLine, Qt.RoundCap))
        
        cx, cy = self.width() // 2, self.height() // 2
        s = 5 # half size
        
        if self.icon_type == 'min':
            painter.drawLine(cx - s, cy, cx + s, cy)
        else: # close
            painter.drawLine(cx - s, cy - s, cx + s, cy + s)
            painter.drawLine(cx - s, cy + s, cx + s, cy - s)

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
    def __init__(self, text, icon_path=None, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedHeight(45)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 10, 0)
        layout.setSpacing(12)
        
        if icon_path and os.path.exists(icon_path):
            self.icon_label = QLabel()
            self.icon_label.setFixedSize(24, 24)
            self.icon_label.setAlignment(Qt.AlignCenter)
            
            # Render SVG at high resolution and scale down for maximum sharpness
            icon = QIcon(icon_path)
            # Use 64x64 for even better interpolation quality
            pixmap = icon.pixmap(64, 64)
            self.icon_label.setPixmap(pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.icon_label.setStyleSheet("background: transparent; border: none;")
            
            # Apply white colorize effect to icons
            color_effect = QGraphicsColorizeEffect()
            color_effect.setColor(QColor("#FFFFFF"))
            color_effect.setStrength(1.0)
            self.icon_label.setGraphicsEffect(color_effect)
            
            layout.addWidget(self.icon_label)
        
        self.text_label = QLabel(text)
        self.text_label.setStyleSheet("background: transparent; color: white; font-weight: 600; font-size: 15px;")
        layout.addWidget(self.text_label)
        layout.addStretch()

class StatusCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusCard")
        self.setMinimumHeight(75)
        
        # Consistent background gradient
        self.setStyleSheet("""
            QFrame#StatusCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1E2430, stop:1 #161B22);
                border: 1px solid rgba(255, 255, 255, 5);
                border-radius: 12px;
            }
        """)

        layout = QGridLayout(self)
        layout.setContentsMargins(15, 12, 12, 12)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(2)

        # Left accent bar (consistent with SummaryCard)
        self.accent_bar = QFrame(self)
        self.accent_bar.setFixedWidth(3)
        self.accent_bar.setStyleSheet("background-color: #a6e3a1; border-radius: 1.5px;")
        
        # Pulsing status dot
        self.dot_container = QWidget()
        self.dot_container.setFixedSize(14, 14)
        dot_layout = QVBoxLayout(self.dot_container)
        dot_layout.setContentsMargins(0,0,0,0)
        
        self.dot = QFrame()
        self.dot.setFixedSize(10, 10)
        self.dot.setStyleSheet("background-color: #a6e3a1; border-radius: 5px;")
        dot_layout.addWidget(self.dot, 0, Qt.AlignCenter)

        # Pulse effect
        self.pulse_effect = QGraphicsOpacityEffect(self.dot)
        self.dot.setGraphicsEffect(self.pulse_effect)
        
        self.pulse_anim = QPropertyAnimation(self.pulse_effect, b"opacity")
        self.pulse_anim.setDuration(1200)
        self.pulse_anim.setStartValue(0.4)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.pulse_anim.setLoopCount(-1) # Infinite
        self.pulse_anim.start()

        self.title = QLabel("Tracking Active")
        self.title.setStyleSheet("color: #a6e3a1; font-size: 14px; font-weight: 800; background: transparent;")
        
        self.subtitle = QLabel("Started at --:--")
        self.subtitle.setStyleSheet("color: #94A3B8; font-size: 12px; background: transparent;")
        
        layout.addWidget(self.dot_container, 0, 0)
        layout.addWidget(self.title, 0, 1)
        layout.addWidget(self.subtitle, 1, 1)
        layout.setColumnStretch(1, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position accent bar
        bar_h = int(self.height() * 0.5)
        self.accent_bar.setFixedHeight(bar_h)
        self.accent_bar.move(0, (self.height() - bar_h) // 2)

    def set_active(self, is_active, start_time="--:--"):
        color = "#a6e3a1" if is_active else "#f9e2af"
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        self.accent_bar.setStyleSheet(f"background-color: {color}; border-radius: 1.5px;")
        
        if is_active:
            self.title.setText("Tracking Active")
            self.title.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 800; background: transparent;")
            self.subtitle.setText(f"Started at {start_time}")
            if self.pulse_anim.state() == QPropertyAnimation.Stopped:
                self.pulse_anim.start()
        else:
            self.title.setText("Tracking Paused")
            self.title.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 800; background: transparent;")
            self.subtitle.setText("System Idle")
            self.pulse_anim.stop()
            self.pulse_effect.setOpacity(1.0)

class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(230)
        self.setObjectName("Sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(10)

        self.logo = QLabel("TIME FORGE")
        self.logo.setObjectName("SidebarLogo")
        self.logo.setAlignment(Qt.AlignCenter)
        
        # Native Electric Indigo glow
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(15)
        glow.setColor(QColor("#6366F1"))
        glow.setOffset(0, 0)
        self.logo.setGraphicsEffect(glow)
        
        layout.addWidget(self.logo)
        layout.addSpacing(20)

        # Paths to icons
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons")
        
        self.btn_home = SidebarButton("Dashboard", os.path.join(base_path, "home.svg"))
        self.btn_stats = SidebarButton("Analytics", os.path.join(base_path, "analytics.svg"))
        self.btn_apps = SidebarButton("Tracked Apps", os.path.join(base_path, "apps.svg"))
        self.btn_settings = SidebarButton("Settings", os.path.join(base_path, "settings.svg"))

        self.buttons = [self.btn_home, self.btn_stats, self.btn_apps, self.btn_settings]
        for btn in self.buttons:
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # Subtle divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #1E2430; border: none;")
        layout.addWidget(divider)
        layout.addSpacing(8)
        
        # Status Card
        self.status_card = StatusCard()
        layout.addWidget(self.status_card)

    def set_active_button(self, index):
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)

class SummaryCard(QFrame):
    def __init__(self, title, value, accent="#89b4fa", grad_start="#151C2B", grad_end="#111827", icon_path=None):
        super().__init__()
        self.accent = QColor(accent)
        self.setMinimumHeight(110)
        self.setCursor(Qt.PointingHandCursor)

        # Main card styling (no border-left here)
        self.setStyleSheet(f"""
            SummaryCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {grad_start}, stop:1 {grad_end});
                border-radius: 12px;
                border: none;
            }}
        """)

        # Softened accent bar as a child widget for rounded ends
        self.accent_bar = QFrame(self)
        ac = QColor(accent)
        bar_color = f"rgba({ac.red()},{ac.green()},{ac.blue()},0.8)"
        self.accent_bar.setStyleSheet(f"""
            background-color: {bar_color};
            border-radius: 1.5px;
        """)
        self.accent_bar.setFixedWidth(3)
        # Position it vertically centered in resizeEvent or just set height here
        self.accent_bar.move(0, 20)
        self.accent_bar.setFixedHeight(70)

        # Hover glow effect
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(0)
        self._glow.setColor(self.accent)
        self._glow.setOffset(0, 2)
        self.setGraphicsEffect(self._glow)

        self._glow_anim = QPropertyAnimation(self._glow, b"blurRadius")
        self._glow_anim.setDuration(200)
        self._glow_anim.setEasingCurve(QEasingCurve.OutCubic)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 14, 15, 14) # Increased left margin to clear the bar
        layout.setSpacing(0)

        # Top row: title + icon
        top_row = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            f"color: {accent}; font-size: 11px; text-transform: uppercase; "
            "font-weight: bold; letter-spacing: 1px; background: transparent;"
        )
        top_row.addWidget(self.title_label)
        top_row.addStretch()

        if icon_path and os.path.exists(icon_path):
            icon_lbl = QLabel()
            icon_lbl.setFixedSize(20, 20)
            icon_lbl.setAlignment(Qt.AlignCenter)
            # Tint icon to semi-transparent white for a subtle decorative look
            source_pixmap = QIcon(icon_path).pixmap(40, 40)
            tinted = QPixmap(source_pixmap.size())
            tinted.fill(Qt.transparent)
            p = QPainter(tinted)
            p.drawPixmap(0, 0, source_pixmap)
            p.setCompositionMode(QPainter.CompositionMode_SourceIn)
            p.fillRect(tinted.rect(), QColor(255, 255, 255, 80))
            p.end()
            icon_lbl.setPixmap(tinted.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon_lbl.setStyleSheet("background: transparent;")
            top_row.addWidget(icon_lbl)

        layout.addLayout(top_row)

        # Subtle separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(255,255,255,8); border: none; margin: 6px 0px;")
        layout.addWidget(sep)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            "color: #F1F5F9; font-size: 28px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(self.value_label)
        layout.addStretch()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep the accent bar centered vertically and pinned to the left
        bar_height = int(self.height() * 0.6)
        self.accent_bar.setFixedHeight(bar_height)
        self.accent_bar.move(0, (self.height() - bar_height) // 2)

    def enterEvent(self, event):
        self._glow_anim.stop()
        self._glow_anim.setStartValue(self._glow.blurRadius())
        self._glow_anim.setEndValue(25)
        self._glow_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._glow_anim.stop()
        self._glow_anim.setStartValue(self._glow.blurRadius())
        self._glow_anim.setEndValue(0)
        self._glow_anim.start()
        super().leaveEvent(event)

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
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons")
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        self.total_usage_card = SummaryCard(
            "Total Usage", "00:00:00",
            accent="#89b4fa", grad_start="#151C2B", grad_end="#111827",
            icon_path=os.path.join(base_path, "clock.svg")
        )
        self.top_app_card = SummaryCard(
            "Most Used App", "None",
            accent="#f38ba8", grad_start="#1F1520", grad_end="#161019",
            icon_path=os.path.join(base_path, "trophy.svg")
        )
        self.session_card = SummaryCard(
            "Current Session", "00:00:00",
            accent="#fab387", grad_start="#1F1A14", grad_end="#16120E",
            icon_path=os.path.join(base_path, "bolt.svg")
        )
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
            QMainWindow, QWidget#MainContainer {
                background-color: #161B22;
                color: #CDD6F4;
                font-family: 'Inter', 'Segoe UI Semibold', 'Segoe UI', sans-serif;
            }
            Sidebar {
                background-color: #0F1117;
                border-right: 1px solid #1E2430;
            }
            QLabel#SidebarLogo {
                color: #6366F1;
                font-size: 22px;
                font-weight: 900;
                letter-spacing: 2px;
                padding: 15px 5px;
            }
            SidebarButton {
                background-color: transparent;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding-left: 15px;
                font-weight: 600;
                font-size: 15px;
                margin: 4px 12px;
            }
            SidebarButton QLabel {
                color: #FFFFFF;
            }
            SidebarButton:hover {
                background-color: rgba(99, 102, 241, 0.1);
            }
            SidebarButton:hover QLabel {
                color: #FFFFFF;
            }
            SidebarButton:checked {
                background-color: rgba(99, 102, 241, 0.15);
                border-left: 4px solid #6366F1;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
            }
            SidebarButton:checked QLabel {
                color: #FFFFFF;
            }
            QFrame#StatusCard {
                background-color: #1E2430;
                border: 1px solid #2D3748;
                border-radius: 12px;
            }
            QLabel#StatusTitle {
                color: #10B981;
                font-size: 15px;
                font-weight: bold;
            }
            QLabel#StatusSub {
                color: #94A3B8;
                font-size: 13px;
            }
            QListWidget {
                background-color: transparent;
                border-radius: 12px;
                border: 1px solid #1E2430;
                color: #CDD6F4;
                padding: 8px;
            }
            QListWidget::item {
                padding: 14px 16px;
                background-color: #1E2430;
                border-radius: 8px;
                margin-bottom: 6px;
                border-left: 3px solid transparent;
            }
            QListWidget::item:hover {
                background-color: #252D3A;
                border-left: 3px solid #6366F1;
            }
            QListWidget::item:selected {
                background-color: rgba(99, 102, 241, 0.15);
                border-left: 3px solid #6366F1;
                color: #A5B4FC;
            }
            QPushButton {
                background-color: #1E2430;
                color: #CDD6F4;
                border: 1px solid #2D3748;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2D3748;
                border-color: #6366F1;
            }
            QPushButton:pressed {
                background-color: #0F1117;
            }
            QGroupBox {
                border: 1px solid #1E2430;
                border-radius: 12px;
                margin-top: 20px;
                color: #94A3B8;
                font-weight: bold;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
            QWidget#ContentArea {
                background: qradialgradient(cx:0.8, cy:0.2, radius:1.0,
                    fx:0.8, fy:0.2,
                    stop:0 #1a1f2e, stop:1 #161B22);
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
        content_widget.setObjectName("ContentArea")
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # Custom Title Bar for Content Area
        title_bar = QWidget()
        title_bar.setFixedHeight(45)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(0, 0, 12, 0)
        title_bar_layout.addStretch()
        
        # Minimize Button
        self.btn_min = WindowButton('min', "#6366F1") # Indigo theme
        self.btn_min.clicked.connect(self.showMinimized)
        
        # Close Button
        self.btn_close = WindowButton('close', "#f38ba8") # Rose theme
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
            self.summary_view.recent_list.setIconSize(QSize(32, 32))
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
