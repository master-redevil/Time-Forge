from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QListWidget, QListWidgetItem, QFileIconProvider, QStyle,
    QFrame, QGridLayout, QScrollArea, QGroupBox, QGraphicsDropShadowEffect, QGraphicsColorizeEffect,
    QGraphicsOpacityEffect, QApplication, QAbstractItemView, QLineEdit, QCalendarWidget, QMenu, QWidgetAction
)
from PySide6.QtCore import Qt, QTimer, QFileInfo, Signal, QSize, QPropertyAnimation, QEasingCurve, QRect, QDateTime, QDate, QMargins
from PySide6.QtGui import QPainter, QColor, QFont, QIcon, QPixmap, QBrush, QPainterPath, QLinearGradient, QPen
from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries, QBarSeries, QStackedBarSeries, QBarSet, 
    QBarCategoryAxis, QValueAxis, QLineSeries, QDateTimeAxis
)
import database
import os
import psutil
import time
import ctypes
from ctypes import wintypes
import datetime
import math
from PySide6.QtCore import Property

class SmoothScrollList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        
        self._scroll_anim = QPropertyAnimation(self.verticalScrollBar(), b"value")
        self._scroll_anim.setDuration(300)
        self._scroll_anim.setEasingCurve(QEasingCurve.OutCubic)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        target = self.verticalScrollBar().value() - delta
        
        self._scroll_anim.stop()
        self._scroll_anim.setStartValue(self.verticalScrollBar().value())
        self._scroll_anim.setEndValue(max(self.verticalScrollBar().minimum(), 
                                         min(target, self.verticalScrollBar().maximum())))
        self._scroll_anim.start()

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

        # Hover animation properties
        self._hover_alpha = 0
        self.hover_anim = QPropertyAnimation(self, b"hover_alpha")
        self.hover_anim.setDuration(250)
        self.hover_anim.setEasingCurve(QEasingCurve.OutCubic)

    @Property(int)
    def hover_alpha(self): return self._hover_alpha
    @hover_alpha.setter
    def hover_alpha(self, v):
        self._hover_alpha = v
        self.update()

    def enterEvent(self, event):
        self.hover_anim.stop()
        self.hover_anim.setStartValue(self._hover_alpha)
        self.hover_anim.setEndValue(30) # ~0.12 opacity
        self.hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_anim.stop()
        self.hover_anim.setStartValue(self._hover_alpha)
        self.hover_anim.setEndValue(0)
        self.hover_anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect().adjusted(12, 4, -12, -4)
        
        if self.isChecked():
            # Active state background
            painter.setBrush(QColor(99, 102, 241, 45))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 8, 8)
            
            # Left accent indicator (pill shape)
            painter.setBrush(QColor("#6366F1"))
            painter.drawRoundedRect(0, 12, 4, self.height() - 24, 2, 2)
        elif self._hover_alpha > 0:
            # Hover state background
            painter.setBrush(QColor(99, 102, 241, self._hover_alpha))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 8, 8)
        
        # Child widgets (labels) will paint themselves after this


class StatusCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusCard")
        self.setMinimumHeight(75)
        
        # Consistent background gradient - now more vibrant
        self.setStyleSheet("""
            QFrame#StatusCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #13251F, stop:1 #0C1412);
                border: 1px solid rgba(16, 185, 129, 0.1);
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
        color = "#10B981" if is_active else "#F59E0B"
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

        # Custom Image Logo
        self.logo = QLabel()
        self.logo.setObjectName("SidebarLogo")
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setContentsMargins(10, 10, 10, 10)
        
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Scale to reasonable width while maintaining aspect ratio
            scaled_pixmap = pixmap.scaledToWidth(160, Qt.SmoothTransformation)
            self.logo.setPixmap(scaled_pixmap)
        else:
            self.logo.setText("TIME FORGE")
            self.logo.setStyleSheet("color: #6366F1; font-size: 22px; font-weight: 900; letter-spacing: 2px;")
        
        # Native Electric Indigo glow
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(20)
        glow.setColor(QColor("#6366F1"))
        glow.setOffset(0, 0)
        self.logo.setGraphicsEffect(glow)
        
        layout.addWidget(self.logo)
        layout.addSpacing(15)

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
            accent="#3B82F6", grad_start="#1E293B", grad_end="#0F172A",
            icon_path=os.path.join(base_path, "clock.svg")
        )
        self.top_app_card = SummaryCard(
            "Most Used App", "None",
            accent="#F43F5E", grad_start="#31141A", grad_end="#1A0A0E",
            icon_path=os.path.join(base_path, "trophy.svg")
        )
        self.session_card = SummaryCard(
            "Current Session", "00:00:00",
            accent="#F59E0B", grad_start="#312012", grad_end="#1A1208",
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
        
        self.recent_list = SmoothScrollList()
        self.recent_list.setObjectName("RecentList")
        layout.addWidget(self.recent_list, 1) # Give it stretch

class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, parent=None, active_color="#6366F1", bg_color="#2D3748"):
        super().__init__(parent)
        self.setFixedSize(44, 22)
        self.setCursor(Qt.PointingHandCursor)
        
        self._active_color = QColor(active_color)
        self._bg_color = QColor(bg_color)
        self._circle_color = QColor("#FFFFFF")
        
        self._status = False
        self._thumb_pos = 2
        
        self._anim = QPropertyAnimation(self, b"thumb_pos")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    @Property(float)
    def thumb_pos(self): return self._thumb_pos
    @thumb_pos.setter
    def thumb_pos(self, pos):
        self._thumb_pos = pos
        self.update()

    def setChecked(self, status):
        if self._status == status: return
        self._status = status
        self._anim.stop()
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(24 if status else 2)
        self._anim.start()

    def isChecked(self):
        return self._status

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._status)
            self.toggled.emit(self._status)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 11, 11)
        
        bg_color = self._active_color if self._status else self._bg_color
        painter.fillPath(path, bg_color)
        
        # Thumb
        painter.setBrush(self._circle_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(self._thumb_pos), 2, 18, 18)

class AppListItemWidget(QWidget):
    toggled = Signal(str, bool)

    def __init__(self, app_name, display_name, exe_path=None, is_tracked=False, parent=None):
        super().__init__(parent)
        self.app_name = app_name
        self.setFixedHeight(60)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(15)
        
        # Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        if exe_path and os.path.exists(exe_path):
            file_info = QFileInfo(exe_path)
            icon = QFileIconProvider().icon(file_info)
            pixmap = icon.pixmap(32, 32)
            self.icon_label.setPixmap(pixmap)
        else:
            # Fallback icon or generic app icon
            self.icon_label.setText("📦")
            self.icon_label.setStyleSheet("font-size: 20px;")
            
        layout.addWidget(self.icon_label)
        
        # Name
        self.name_label = QLabel(display_name)
        self.name_label.setStyleSheet("color: white; font-weight: 600; font-size: 14px;")
        layout.addWidget(self.name_label)
        
        layout.addStretch()
        
        # Toggle
        self.toggle = ToggleSwitch()
        self.toggle.setChecked(is_tracked)
        self.toggle.toggled.connect(lambda checked: self.toggled.emit(self.app_name, checked))
        layout.addWidget(self.toggle)

class SettingsView(QWidget):
    apps_changed = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 20)
        layout.setSpacing(15)
        
        # Header Row
        header_layout = QHBoxLayout()
        header = QLabel("App Management")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #f5e0dc;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search applications...")
        self.search_input.setFixedWidth(250)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1E2430;
                border: 1px solid #2D3748;
                border-radius: 8px;
                padding: 8px 12px;
                color: #CDD6F4;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #6366F1;
            }
        """)
        self.search_input.textChanged.connect(self.filter_apps)
        header_layout.addWidget(self.search_input)
        
        # Refresh Button
        self.btn_refresh = QPushButton()
        self.btn_refresh.setFixedSize(36, 36)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #1E2430;
                border: 1px solid #2D3748;
                border-radius: 8px;
                color: #CDD6F4;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #2D3748;
                border-color: #6366F1;
            }
        """)
        self.btn_refresh.setText("🔄")
        self.btn_refresh.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.btn_refresh)
        
        layout.addLayout(header_layout)

        # App List
        self.app_list = SmoothScrollList()
        self.app_list.setObjectName("SettingsAppList")
        self.app_list.setStyleSheet("""
            QListWidget#SettingsAppList {
                background-color: transparent;
                border: none;
            }
            QListWidget#SettingsAppList::item {
                background-color: #1E2430;
                border-radius: 12px;
                margin-bottom: 8px;
                padding: 0px;
            }
            QListWidget#SettingsAppList::item:hover {
                background-color: #252D3A;
            }
        """)
        layout.addWidget(self.app_list)

        self.all_apps_data = [] # List of dicts: {name, display_name, exe, tracked}

    def clean_name(self, name):
        if name.lower().endswith('.exe'):
            return name[:-4].title()
        return name.title()

    def refresh_data(self):
        self.load_all_apps()
        self.filter_apps()

    def load_all_apps(self):
        # Get running processes
        running = {} # name -> exe
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                name = proc.info.get('name')
                exe = proc.info.get('exe')
                if name:
                    name_lower = name.lower()
                    if exe and name_lower not in running:
                        running[name_lower] = exe
                    elif name_lower not in running:
                        running[name_lower] = None
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Get tracked apps
        tracked_apps = database.get_tracked_apps()
        tracked_set = set(tracked_apps)
        
        self.all_apps_data = []
        
        # Merge tracked apps
        for app in tracked_apps:
            self.all_apps_data.append({
                'name': app,
                'display_name': self.clean_name(app),
                'exe': running.get(app), # Try to get current exe path if running
                'tracked': True
            })
            if app in running:
                del running[app]
        
        # Add remaining running apps
        for app, exe in running.items():
            self.all_apps_data.append({
                'name': app,
                'display_name': self.clean_name(app),
                'exe': exe,
                'tracked': False
            })
        
        # Sort by display name
        self.all_apps_data.sort(key=lambda x: x['display_name'])

    def filter_apps(self):
        search_text = self.search_input.text().lower()
        self.app_list.clear()
        
        for app_data in self.all_apps_data:
            if search_text and search_text not in app_data['display_name'].lower():
                continue
                
            item = QListWidgetItem(self.app_list)
            item.setSizeHint(QSize(0, 60))
            
            widget = AppListItemWidget(
                app_data['name'], 
                app_data['display_name'], 
                app_data['exe'], 
                app_data['tracked']
            )
            widget.toggled.connect(self.handle_toggle)
            
            self.app_list.addItem(item)
            self.app_list.setItemWidget(item, widget)

    def handle_toggle(self, app_name, checked):
        if checked:
            exe_path = next((a['exe'] for a in self.all_apps_data if a['name'] == app_name), None)
            if not database.add_tracked_app(app_name, exe_path):
                if exe_path:
                    database.update_app_path(app_name, exe_path)
        else:
            database.remove_tracked_app(app_name)
        
        for app in self.all_apps_data:
            if app['name'] == app_name:
                app['tracked'] = checked
                break
                
        self.apps_changed.emit()

    def load_tracked_apps(self):
        self.refresh_data()

class TimelineWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(400)
        self.sessions = []
        self.selected_date = QDate.currentDate()
        self.app_colors = {}
        self.colors = ["#89b4fa", "#f38ba8", "#a6e3a1", "#f9e2af", "#cba6f7", "#89dceb", "#fab387"]

    def set_data(self, sessions, date):
        self.sessions = sessions
        self.selected_date = date
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw Background
        painter.fillRect(self.rect(), QColor("#1E2430"))
        
        # Margins
        left_margin = 100
        right_margin = 30
        top_margin = 40
        bottom_margin = 40
        
        draw_rect = self.rect().adjusted(left_margin, top_margin, -right_margin, -bottom_margin)
        w = draw_rect.width()
        h = draw_rect.height()
        
        if not self.sessions:
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(self.rect(), Qt.AlignCenter, "No session data for this day")
            return

        # Draw Hour Lines
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
        for hour in range(25):
            x = draw_rect.left() + (hour / 24.0) * w
            painter.drawLine(int(x), draw_rect.top(), int(x), draw_rect.bottom())
            if hour % 4 == 0:
                painter.setPen(QColor("#64748B"))
                font = painter.font()
                font.setPointSize(8)
                painter.setFont(font)
                painter.drawText(int(x) - 15, draw_rect.bottom() + 20, f"{hour:02}:00")
                painter.setPen(QPen(QColor(255, 255, 255, 10), 1))

        # Draw Current Time Indicator (if viewing today)
        if self.selected_date == QDate.currentDate():
            now = QDateTime.currentDateTime().time()
            now_sec = now.hour() * 3600 + now.minute() * 60 + now.second()
            x_now = draw_rect.left() + (now_sec / (24.0 * 3600)) * w
            painter.setPen(QPen(QColor("#F43F5E"), 2, Qt.DashLine))
            painter.drawLine(int(x_now), draw_rect.top(), int(x_now), draw_rect.bottom())
            painter.setBrush(QColor("#F43F5E"))
            painter.drawEllipse(int(x_now) - 3, draw_rect.top() - 3, 6, 6)

        # Get unique apps for swimlanes
        apps_list = sorted(list(set(s['app'] for s in self.sessions)))
        row_h = min(40, h / max(len(apps_list), 1))
        
        # Draw Session Blocks
        for session in self.sessions:
            app = session['app']
            if app not in self.app_colors:
                self.app_colors[app] = QColor(self.colors[len(self.app_colors) % len(self.colors)])
            
            color = self.app_colors[app]
            
            try:
                # Parse start date/time
                # sqlite returns YYYY-MM-DDTHH:MM:SS
                dt = QDateTime.fromString(session['start'], Qt.ISODate)
                time_obj = dt.time()
                start_sec = time_obj.hour() * 3600 + time_obj.minute() * 60 + time_obj.second()
                duration = session['duration']
                
                x_start = draw_rect.left() + (start_sec / (24.0 * 3600)) * w
                x_width = (duration / (24.0 * 3600)) * w
                x_width = max(x_width, 3) # Min width
                
                app_idx = apps_list.index(app)
                y = draw_rect.top() + app_idx * row_h
                
                block_rect = QRect(int(x_start), int(y) + 5, int(x_width), int(row_h) - 10)
                
                # Highlight block
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(block_rect, 4, 4)
                
                # Subtle glow
                glow_color = QColor(color)
                glow_color.setAlpha(40)
                painter.setBrush(glow_color)
                painter.drawRoundedRect(block_rect.adjusted(-2, -2, 2, 2), 6, 6)
                
            except Exception as e:
                continue

        # Draw App Labels
        for i, app in enumerate(apps_list):
            y = draw_rect.top() + i * row_h
            painter.setPen(QColor("#CDD6F4"))
            font = painter.font()
            font.setBold(True)
            font.setPointSize(9)
            painter.setFont(font)
            display_name = app[:-4].title() if app.lower().endswith('.exe') else app.title()
            painter.drawText(15, int(y + row_h/2 + 5), display_name)

class AnalyticsView(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_date = QDate.currentDate()
        self.setup_ui()
        # Data will be loaded when switch_view is called or initially
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 20)
        layout.setSpacing(20)
        
        # Header Row
        header_layout = QHBoxLayout()
        header = QLabel("Usage Analytics")
        header.setStyleSheet("font-size: 26px; font-weight: bold; color: #f5e0dc;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        # Date Selector
        self.date_btn = QPushButton(self.selected_date.toString("MMM dd, yyyy"))
        self.date_btn.setFixedWidth(180)
        self.date_btn.setCursor(Qt.PointingHandCursor)
        self.date_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E2430;
                border: 1px solid #2D3748;
                border-radius: 10px;
                padding: 10px 15px;
                color: #CDD6F4;
                font-weight: 800;
                font-size: 13px;
                text-align: left;
            }
            QPushButton:hover {
                border-color: #6366F1;
                background-color: #252D3A;
            }
        """)
        self.date_btn.clicked.connect(self.show_calendar)
        header_layout.addWidget(self.date_btn)
        layout.addLayout(header_layout)

        # Tab Bar
        tab_container = QWidget()
        tab_container.setFixedHeight(50)
        tab_layout = QHBoxLayout(tab_container)
        tab_layout.setContentsMargins(0,0,0,0)
        tab_layout.setSpacing(10)
        
        self.tabs = []
        for name in ["Daily Overview", "Trends", "Timeline"]:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #94A3B8;
                    border: none;
                    border-bottom: 2px solid transparent;
                    font-weight: 600;
                    font-size: 14px;
                    padding: 0 15px;
                }
                QPushButton:hover {
                    color: #CDD6F4;
                }
                QPushButton:checked {
                    color: #6366F1;
                    border-bottom: 2px solid #6366F1;
                }
            """)
            tab_layout.addWidget(btn)
            self.tabs.append(btn)
        
        self.tabs[0].setChecked(True)
        self.tabs[0].clicked.connect(lambda: self.switch_tab(0))
        self.tabs[1].clicked.connect(lambda: self.switch_tab(1))
        self.tabs[2].clicked.connect(lambda: self.switch_tab(2))
        tab_layout.addStretch()
        layout.addWidget(tab_container)

        # Content Stack
        self.stack = QStackedWidget()
        
        # Overview Tab
        self.overview_tab = QWidget()
        ov_layout = QHBoxLayout(self.overview_tab)
        ov_layout.setContentsMargins(0,0,0,0)
        
        self.bar_chart = QChart()
        self.bar_chart.setBackgroundBrush(QColor(0,0,0,0))
        self.bar_chart.legend().setLabelColor(QColor("#CDD6F4"))
        self.bar_view = QChartView(self.bar_chart)
        self.bar_view.setRenderHint(QPainter.Antialiasing)
        
        self.pie_chart = QChart()
        self.pie_chart.setBackgroundBrush(QColor(0,0,0,0))
        self.pie_chart.legend().setVisible(False) # Use custom legend
        self.pie_view = QChartView(self.pie_chart)
        self.pie_view.setRenderHint(QPainter.Antialiasing)
        
        # Custom Legend Widget
        self.legend_widget = QWidget()
        self.legend_layout = QGridLayout(self.legend_widget)
        self.legend_layout.setContentsMargins(10, 0, 10, 0)
        self.legend_layout.setHorizontalSpacing(15)
        self.legend_layout.setVerticalSpacing(2)
        self.legend_layout.setColumnStretch(0, 1)
        self.legend_layout.setColumnStretch(1, 1)
        
        pie_container = QVBoxLayout()
        pie_container.addWidget(self.pie_view, 1)
        pie_container.addWidget(self.legend_widget)
        
        ov_layout.addWidget(self.bar_view, 3)
        ov_layout.addLayout(pie_container, 2)
        
        # Trends Tab
        self.trends_tab = QWidget()
        tr_layout = QVBoxLayout(self.trends_tab)
        self.line_chart = QChart()
        self.line_chart.setBackgroundBrush(QColor(0,0,0,0))
        self.line_chart.legend().setLabelColor(QColor("#CDD6F4"))
        self.line_view = QChartView(self.line_chart)
        self.line_view.setRenderHint(QPainter.Antialiasing)
        tr_layout.addWidget(self.line_view)
        
        # Timeline Tab
        self.timeline_widget = TimelineWidget()
        
        self.stack.addWidget(self.overview_tab)
        self.stack.addWidget(self.trends_tab)
        self.stack.addWidget(self.timeline_widget)
        
        layout.addWidget(self.stack)

        # Animation setup
        self.opacity_effect = QGraphicsOpacityEffect(self.stack)
        self.stack.setGraphicsEffect(self.opacity_effect)
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

    def switch_tab(self, index):
        if self.stack.currentIndex() == index: return
        
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        
        for i, btn in enumerate(self.tabs):
            btn.setChecked(i == index)
        
        self.stack.setCurrentIndex(index)
        self.refresh_data()
        self.anim.start()

    def show_calendar(self):
        menu = QMenu(self)
        calendar = QCalendarWidget()
        calendar.setSelectedDate(self.selected_date)
        calendar.setGridVisible(False)
        calendar.setStyleSheet("""
            QCalendarWidget QWidget { background-color: #1E2430; color: #CDD6F4; }
            QCalendarWidget QToolButton { color: white; background-color: #2D3748; border-radius: 5px; margin: 5px; }
            QCalendarWidget QAbstractItemView:enabled { color: #CDD6F4; selection-background-color: #6366F1; selection-color: white; }
            QCalendarWidget QAbstractItemView:disabled { color: #4B5563; }
        """)
        
        action = QWidgetAction(menu)
        action.setDefaultWidget(calendar)
        menu.addAction(action)
        
        calendar.clicked.connect(lambda d: self.set_date(d, menu))
        menu.exec(self.date_btn.mapToGlobal(self.date_btn.rect().bottomLeft()))

    def set_date(self, date, menu):
        self.selected_date = date
        self.date_btn.setText(date.toString("MMM dd, yyyy"))
        menu.close()
        self.refresh_data()

    def refresh_data(self):
        date_iso = self.selected_date.toPython().isoformat()
        idx = self.stack.currentIndex()
        
        if idx == 0:
            usage = database.get_usage_for_date(date_iso)
            self.update_overview(usage)
        elif idx == 1:
            history = database.get_device_activity_history(7)
            self.update_trends(history)
        elif idx == 2:
            sessions = database.get_sessions_for_date(date_iso)
            self.timeline_widget.set_data(sessions, self.selected_date)

    def update_overview(self, usage):
        if not usage:
            self.bar_chart.removeAllSeries()
            self.pie_chart.removeAllSeries()
            return

        sorted_usage = sorted(usage.items(), key=lambda x: x[1], reverse=True)[:7]
        app_names = [app[:-4].title() if app.lower().endswith('.exe') else app.title() for app, sec in sorted_usage]
        
        # Determine optimal bar width based on data volume
        count = len(sorted_usage)
        if count <= 2: bar_width = 0.75
        elif count <= 4: bar_width = 0.6
        elif count <= 5: bar_width = 0.45
        else: bar_width = 0.35 # "Thinner only when full"

        # Check if we can update in-place to prevent layout flicker
        current_series = self.bar_chart.series()
        can_update = (len(current_series) == 1 and 
                     isinstance(current_series[0], QStackedBarSeries) and 
                     current_series[0].count() == count and
                     len(self.pie_chart.series()) > 0)
        
        colors = ["#89b4fa", "#f38ba8", "#a6e3a1", "#f9e2af", "#cba6f7", "#89dceb", "#fab387"]

        if can_update:
            series = current_series[0]
            series.setBarWidth(bar_width)
            max_val = 0
            for i, (app, sec) in enumerate(sorted_usage):
                val = sec / 60.0
                if val > max_val: max_val = val
                bset = series.barSets()[i]
                for j in range(count):
                    bset.replace(j, val if i == j else 0)
            
            if self.bar_chart.axes(Qt.Vertical):
                self.bar_chart.axes(Qt.Vertical)[0].setRange(0, max(1, max_val * 1.2))
            
            # Update Pie Chart values
            pie_series = self.pie_chart.series()[0]
            for i, (app, sec) in enumerate(sorted_usage[:5]):
                if i < len(pie_series.slices()):
                    pie_series.slices()[i].setValue(sec)
            
            self.update_custom_legend(sorted_usage[:5], colors)
        else:
            self.bar_chart.removeAllSeries()
            for ax in self.bar_chart.axes(): self.bar_chart.removeAxis(ax)
            self.pie_chart.removeAllSeries()

            # Using a single QStackedBarSeries allows bars to fill the category slots properly
            main_series = QStackedBarSeries()
            main_series.setBarWidth(bar_width)
            
            max_val = 0
            for i, (app, sec) in enumerate(sorted_usage):
                val = sec / 60.0
                if val > max_val: max_val = val
                bset = QBarSet(app_names[i])
                for j in range(count):
                    bset.append(val if i == j else 0)
                bset.setColor(QColor(colors[i % len(colors)]))
                bset.setBorderColor(Qt.transparent)
                main_series.append(bset)
            
            self.bar_chart.addSeries(main_series)
            self.bar_chart.setMargins(QMargins(15, 10, 15, 45))
            
            axis_x = QBarCategoryAxis()
            axis_x.append(app_names)
            axis_x.setLabelsColor(QColor("#CDD6F4"))
            axis_x.setLabelsAngle(-45)
            font = axis_x.labelsFont()
            font.setPointSize(8)
            axis_x.setLabelsFont(font)
            axis_x.setGridLineVisible(False)
            self.bar_chart.addAxis(axis_x, Qt.AlignBottom)
            main_series.attachAxis(axis_x)
            
            axis_y = QValueAxis()
            axis_y.setRange(0, max(1, max_val * 1.2))
            axis_y.setTickCount(6)
            axis_y.setLabelFormat("%d m")
            axis_y.setLabelsColor(QColor("#CDD6F4"))
            axis_y.setGridLineColor(QColor(255, 255, 255, 20))
            self.bar_chart.addAxis(axis_y, Qt.AlignLeft)
            main_series.attachAxis(axis_y)

            pie_series = QPieSeries()
            pie_series.setHoleSize(0.45) 
            for i, (app, sec) in enumerate(sorted_usage[:5]):
                slice = pie_series.append(app_names[i], sec)
                slice.setBrush(QColor(colors[i % len(colors)]))
                slice.setLabelVisible(False) 
                slice.setBorderWidth(0)
            self.pie_chart.addSeries(pie_series)
            self.update_custom_legend(sorted_usage[:5], colors)

    def update_custom_legend(self, usage_subset, colors):
        # Correctly clear existing legend widgets
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            
        for i, (app, sec) in enumerate(usage_subset):
            name = app[:-4].title() if app.lower().endswith('.exe') else app.title()
            
            # Wrap each legend item in a QWidget for easier cleanup and layout
            item_widget = QWidget()
            row = QHBoxLayout(item_widget)
            row.setContentsMargins(5, 4, 5, 4)
            row.setSpacing(10)
            
            dot = QLabel()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background-color: {colors[i % len(colors)]}; border-radius: 6px;")
            
            label = QLabel(name)
            label.setStyleSheet("color: #CDD6F4; font-size: 12px; font-weight: 600;")
            label.setWordWrap(True)
            
            row.addWidget(dot)
            row.addWidget(label)
            row.addStretch()
            
            self.legend_layout.addWidget(item_widget, i // 2, i % 2)

    def update_trends(self, history):
        self.line_chart.removeAllSeries()
        for ax in self.line_chart.axes(): self.line_chart.removeAxis(ax)
        
        if not history: return
        
        series = QLineSeries()
        series.setName("Total Daily Activity")
        pen = QPen(QColor("#6366F1"), 4)
        series.setPen(pen)
        series.setPointsVisible(True)
        series.setPointLabelsVisible(False)
        
        dates = sorted(history.keys())
        categories = []
        max_val = 0
        for i, d in enumerate(dates):
            val = history[d] / 60.0
            series.append(i, val)
            categories.append(d[5:]) # MM-DD
            if val > max_val: max_val = val
            
        self.line_chart.addSeries(series)
        
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsColor(QColor("#CDD6F4"))
        axis_x.setGridLineVisible(False)
        self.line_chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setRange(0, max(1, max_val * 1.2))
        axis_y.setTickCount(6)
        axis_y.setLabelFormat("%d m")
        axis_y.setLabelsColor(QColor("#CDD6F4"))
        axis_y.setGridLineColor(QColor(255, 255, 255, 20))
        self.line_chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

class DashboardWindow(QWidget):
    def __init__(self):
        super().__init__()
        # P1.5: Cache the focused app name from the tracker signal to avoid UI-thread psutil calls
        self.current_focused_app = ""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Set Window Icon from logo.png
        import os
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
            
        self.resize(1000, 650)
        self.center_on_screen()
        # P1.3: Track last refresh to throttle high-frequency updates
        self.last_refresh_time = 0

    def center_on_screen(self):
        # use availableGeometry to exclude taskbar area
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(screen.left() + x, screen.top() + y)
        
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
            SidebarButton QLabel {
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
        self.stats_view = AnalyticsView()
        self.apps_view = QListWidget()
        self.settings_view = SettingsView()
        self.settings_view.apps_changed.connect(self.load_data)

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
        
        # Initial View
        self.switch_view(0)


    def switch_view(self, index):
        self.stacked_widget.setCurrentIndex(index)
        self.sidebar.set_active_button(index)
        if index == 1:
            self.stats_view.refresh_data()
        elif index == 3:
            self.settings_view.load_tracked_apps()
            self.settings_view.search_input.setFocus()
        self.load_data()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            new_pos = event.globalPosition().toPoint()
            diff = new_pos - self.drag_pos
            self.move(self.pos() + diff)
            self.drag_pos = new_pos
        super().mouseMoveEvent(event)

    def load_data(self):
        data = database.get_today_usage()
        tracked_set = set(database.get_tracked_apps())
        filtered_data = {k: v for k, v in data.items() if k in tracked_set}
        app_paths = database.get_app_paths()
        icon_provider = QFileIconProvider()

        def clean_name(name):
            if name.lower().endswith('.exe'):
                return name[:-4].title()
            return name.title()

        cleaned_data = []
        for app in sorted(list(tracked_set)):
            seconds = filtered_data.get(app, 0)
            cleaned_data.append((app, clean_name(app), seconds))
        
        # Sort by usage (descending) but keep all tracked apps
        cleaned_data.sort(key=lambda x: x[2], reverse=True)

        # Update Summary View
        total_device_seconds = database.get_today_device_activity()
        self.summary_view.total_usage_card.value_label.setText(format_time(total_device_seconds))
        
        active_sessions = database.get_active_sessions()
        used_apps = [d for d in cleaned_data if d[2] > 0 or d[0] in active_sessions]

        if used_apps:
            self.summary_view.top_app_card.value_label.setText(used_apps[0][1])
            
            self.summary_view.recent_list.clear()
            self.summary_view.recent_list.setIconSize(QSize(32, 32))
            for app, friendly_name, seconds in used_apps[:5]:
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
        focused = self.current_focused_app
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
        
        # If stats view is visible, refresh it too
        if self.stacked_widget.currentIndex() == 1:
            self.stats_view.refresh_data()


    def refresh(self, focused_app=None, force=False):
        # P1.5: Update cached focused app if provided by the signal
        if focused_app is not None:
            self.current_focused_app = focused_app
            
        # P1.3: Skip refresh if the window is not visible to save CPU and DB resources
        # unless it is a 'forced' refresh (e.g. when opening from tray)
        if not self.isVisible() and not force:
            return
            
        # P1.3: Throttle UI refreshes to 1 second unless forced
        # This allows real-time updates as requested by the user
        now = time.time()
        if not force and now - self.last_refresh_time < 1:
            return
            
        self.last_refresh_time = now
        self.load_data()

    def update_idle_status(self, is_idle):
        self.sidebar.status_card.set_active(not is_idle, self.app_start_time)
