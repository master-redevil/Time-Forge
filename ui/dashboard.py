from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QListWidget, QListWidgetItem, QFileIconProvider, QStyle,
    QFrame, QGridLayout, QScrollArea, QGroupBox, QGraphicsDropShadowEffect, QGraphicsColorizeEffect,
    QGraphicsOpacityEffect, QApplication, QAbstractItemView, QLineEdit, QCalendarWidget, QMenu, QWidgetAction,
    QSpinBox, QProgressBar, QDialog, QFileDialog, QComboBox, QDateEdit
)
import csv
import json
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtCore import Qt, QTimer, QFileInfo, Signal, QSize, QPropertyAnimation, QEasingCurve, QRect, QDateTime, QDate, QMargins, QBuffer, QIODevice
from PySide6.QtGui import QPainter, QColor, QFont, QIcon, QPixmap, QBrush, QPainterPath, QLinearGradient, QPen, QTextDocument, QPageLayout
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
import base64
import datetime
import math
from PySide6.QtCore import Property
import os

SYSTEM_PROCESS_BLOCKLIST = {
    # Core System
    'svchost.exe', 'csrss.exe', 'dwm.exe', 'smss.exe', 'wininit.exe', 'services.exe', 
    'lsass.exe', 'winlogon.exe', 'sihost.exe', 'conhost.exe', 'taskhostw.exe',
    'dllhost.exe', 'runtimebroker.exe', 'ctfmon.exe', 'spoolsv.exe',
    
    # UI & Shell
    'explorer.exe', 'shellexperiencehost.exe', 'startmenuexperiencehost.exe', 
    'searchhost.exe', 'searchindexer.exe', 'searchapp.exe', 'textinputhost.exe',
    'applicationframehost.exe', 'fontdrvhost.exe', 'smartscreen.exe', 'chxsmartscreen.exe',
    
    # Background Services & Maintenance
    'aggregatorhost.exe', 'audiodg.exe', 'securityhealthservice.exe', 'usocoreworker.exe',
    'compattelrunner.exe', 'mscorsvw.exe', 'sppsvc.exe', 'wsappx.exe', 'dashost.exe',
    'backgroundtaskhost.exe', 'agmservice.exe', 'credentialenrollmentmanager.exe',
    'phoneexperiencehost.exe', 'yourphone.exe', 'mobsync.exe', 'msdtc.exe',
    'securityhealthsystray.exe', 'systemsettings.exe',
    
    # Newly Identified Services (Screenshot batch)
    'etdservice.exe', 'filecoauth.exe', 'fmservice64.exe', 'gameinputredistservice.exe',
    'gameinputsvc.exe', 'gamingservices.exe', 'gamingservicesnet.exe', 'hxtsr.exe',
    'ibmpmsvc.exe', 'lsess.exe', 'mousocoreworker.exe', 'onenotem.exe', 'scvhost.exe',
    'spoolsv.exe', 'smartscreen.exe', 'unsecapp.exe', 'wudfhost.exe'
}

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
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{secs:02}"
    return f"{minutes:02}:{secs:02}"

def format_duration_pleasant(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m"
    return f"{int(seconds)}s"

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

    def set_error(self, message):
        color = "#EF4444" # Red
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        self.accent_bar.setStyleSheet(f"background-color: {color}; border-radius: 1.5px;")
        self.title.setText("Tracking Error")
        self.title.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 800; background: transparent;")
        self.subtitle.setText(message[:40] + "..." if len(message) > 40 else message)
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
        self.btn_manage = SidebarButton("App Management", os.path.join(base_path, "management.svg"))
        self.btn_settings = SidebarButton("Settings", os.path.join(base_path, "settings.svg"))

        self.buttons = [self.btn_home, self.btn_stats, self.btn_apps, self.btn_manage, self.btn_settings]
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

class TrackedAppItemWidget(QWidget):
    def __init__(self, app_name, friendly_name, total_seconds, session_seconds, is_active, max_seconds=1, exe_path=None, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(110)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        
        # Card background/container
        self.container = QFrame()
        self.container.setObjectName("AppCard")
        self.container.setStyleSheet("""
            QFrame#AppCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1E2430, stop:1 #161B22);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 14px;
            }
            QFrame#AppCard:hover {
                background: #252D3A;
                border-color: #6366F1;
            }
        """)
        
        card_layout = QVBoxLayout(self.container)
        card_layout.setContentsMargins(15, 12, 15, 12)
        card_layout.setSpacing(10)
        
        # Top Row: Icon + Name + Badge
        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        
        # Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setAlignment(Qt.AlignCenter)
        if exe_path and os.path.exists(exe_path):
            file_info = QFileInfo(exe_path)
            icon = QFileIconProvider().icon(file_info)
            self.icon_label.setPixmap(icon.pixmap(32, 32))
        else:
            self.icon_label.setText("📦")
            self.icon_label.setStyleSheet("font-size: 20px;")
        top_row.addWidget(self.icon_label)
        
        # Name Info
        name_col = QVBoxLayout()
        name_col.setSpacing(0)
        
        self.name_label = QLabel(friendly_name)
        self.name_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background: transparent;")
        name_col.addWidget(self.name_label)
        
        if is_active:
            self.active_badge = QLabel("FOCUSED")
            self.active_badge.setStyleSheet("""
                color: #10B981;
                font-size: 9px;
                font-weight: 900;
                background: transparent;
            """)
            name_col.addWidget(self.active_badge)
        
        top_row.addLayout(name_col)
        top_row.addStretch()
        card_layout.addLayout(top_row)
        
        # Stats
        stats_row = QHBoxLayout()
        self.total_lbl = QLabel(format_time(total_seconds))
        self.total_lbl.setStyleSheet("color: #F1F5F9; font-size: 13px; font-weight: 800; background: transparent;")
        stats_row.addWidget(self.total_lbl)
        
        if session_seconds > 0:
            sess_lbl = QLabel(f"• {format_time(session_seconds)} Session")
            sess_lbl.setStyleSheet("color: #6366F1; font-size: 11px; font-weight: 600; background: transparent;")
            stats_row.addWidget(sess_lbl)
        
        stats_row.addStretch()
        card_layout.addLayout(stats_row)
        
        # Progress Bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        percentage = int((total_seconds / max_seconds) * 100) if max_seconds > 0 else 0
        self.progress.setValue(percentage)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #6366F1;
                border-radius: 2px;
            }
        """)
        card_layout.addWidget(self.progress)
        
        layout.addWidget(self.container)

class TrackedAppsView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(15)
        
        # Header Row
        header_layout = QHBoxLayout()
        header = QLabel("Tracked Applications")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #f5e0dc;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Scrollable Grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(10)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def update_apps(self, cleaned_data, active_sessions, focused_app, app_paths):
        # Clear current grid
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not cleaned_data:
            empty_lbl = QLabel("No applications are currently being tracked.\nGo to 'App Management' to add some!")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #94A3B8; font-size: 14px; margin-top: 50px;")
            self.grid.addWidget(empty_lbl, 0, 0)
            return

        # Calculate max usage for progress bars
        max_usage = max([d[2] for d in cleaned_data]) if cleaned_data else 1
        
        # Build grid (3 columns)
        cols = 3
        for i, (app, friendly_name, seconds) in enumerate(cleaned_data):
            row = i // cols
            col = i % cols
            
            session_seconds = active_sessions.get(app, 0)
            is_active = (app == focused_app)
            exe_path = app_paths.get(app)
            
            card = TrackedAppItemWidget(
                app, friendly_name, seconds, session_seconds, is_active, max_usage, exe_path
            )
            self.grid.addWidget(card, row, col)
        
        # Add stretch at the bottom
        self.grid.setRowStretch(self.grid.rowCount(), 1)

class AppManagementView(QWidget):
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
        self.search_input.setFixedWidth(280)
        
        icons_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons")
        search_icon = QIcon(os.path.join(icons_path, "search.svg"))
        self.search_input.addAction(search_icon, QLineEdit.LeadingPosition)
        
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1E2430;
                border: 1px solid #2D3748;
                border-radius: 8px;
                padding: 8px 8px 8px 35px; /* Increased left padding for icon */
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
        
        refresh_icon = QIcon(os.path.join(icons_path, "refresh.svg"))
        self.btn_refresh.setIcon(refresh_icon)
        self.btn_refresh.setIconSize(QSize(18, 18))
        
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #1E2430;
                border: 1px solid #2D3748;
                border-radius: 8px;
                color: #CDD6F4;
            }
            QPushButton:hover {
                background-color: #2D3748;
                border-color: #6366F1;
            }
        """)
        self.btn_refresh.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.btn_refresh)
        
        # System Apps Toggle
        header_layout.addSpacing(10)
        system_toggle_layout = QHBoxLayout()
        system_toggle_layout.setSpacing(8)
        
        system_label = QLabel("Show System")
        system_label.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        system_toggle_layout.addWidget(system_label)
        
        self.system_toggle = ToggleSwitch()
        self.system_toggle.setChecked(False)
        self.system_toggle.toggled.connect(self.set_show_system)
        system_toggle_layout.addWidget(self.system_toggle)
        
        header_layout.addLayout(system_toggle_layout)
        
        layout.addLayout(header_layout)

        # App List
        self.app_list = SmoothScrollList()
        self.app_list.setObjectName("AppManagementList")
        self.app_list.setStyleSheet("""
            QListWidget#AppManagementList {
                background-color: transparent;
                border: none;
            }
            QListWidget#AppManagementList::item {
                background-color: #1E2430;
                border-radius: 12px;
                margin-bottom: 8px;
                padding: 0px;
            }
            QListWidget#AppManagementList::item:hover {
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

    def set_show_system(self, checked):
        self.show_system_apps = checked
        self.filter_apps()

    def filter_apps(self):
        search_text = self.search_input.text().lower()
        self.app_list.clear()
        
        show_system = getattr(self, 'show_system_apps', False)
        
        for app_data in self.all_apps_data:
            app_name = app_data['name'].lower()
            
            # P3.4: Filter system processes (Blocklist + Path/Name Heuristics)
            exe_path = (app_data.get('exe') or "").lower()
            is_system = app_name in SYSTEM_PROCESS_BLOCKLIST or \
                        (not app_name.endswith('.exe') and f"{app_name}.exe" in SYSTEM_PROCESS_BLOCKLIST) or \
                        "c:\\windows" in exe_path or \
                        "windowsapps" in exe_path or \
                        any(suffix in app_name for suffix in ['service.exe', 'services.exe', 'svc.exe', 'service64.exe'])
            
            if not show_system and is_system:
                continue
                
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

class ModernSpinBox(QSpinBox):
    def __init__(self, min_val=1, max_val=9999, suffix="", parent=None):
        super().__init__(parent)
        self.setRange(min_val, max_val)
        self.setSuffix(suffix)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QSpinBox {
                background-color: #1E2430;
                border: 2px solid #2D3748;
                border-radius: 10px;
                padding: 6px 12px;
                color: #CDD6F4;
                font-size: 14px;
                font-weight: 800;
                min-width: 100px;
            }
            QSpinBox:hover {
                border-color: #4B5563;
            }
            QSpinBox:focus {
                border-color: #6366F1;
                background-color: #252D3A;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px;
            }
        """)

class SettingCard(QFrame):
    def __init__(self, title, description, icon_path=None, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingCard")
        self.setMinimumHeight(130)
        
        # Glassmorphic styling
        self.setStyleSheet("""
            QFrame#SettingCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1E2430, stop:1 #161B22);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Header Row
        header = QHBoxLayout()
        header.setSpacing(12)
        
        if icon_path and os.path.exists(icon_path):
            self.icon_label = QLabel()
            self.icon_label.setFixedSize(28, 28)
            pixmap = QIcon(icon_path).pixmap(28, 28)
            self.icon_label.setPixmap(pixmap)
            
            # Colorize icon
            color_effect = QGraphicsColorizeEffect()
            color_effect.setColor(QColor("#6366F1"))
            self.icon_label.setGraphicsEffect(color_effect)
            header.addWidget(self.icon_label)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #F1F5F9; font-weight: 800; font-size: 15px; background: transparent;")
        header.addWidget(self.title_label)
        header.addStretch()
        
        # Input Slot
        self.input_container = QWidget()
        self.input_layout = QHBoxLayout(self.input_container)
        self.input_layout.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self.input_container)
        layout.addLayout(header)

        # Description
        self.desc_label = QLabel(description)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #94A3B8; font-size: 12px; background: transparent; line-height: 1.5; margin-top: 5px;")
        layout.addWidget(self.desc_label)
        layout.addStretch()

        # Hover Effect
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(0)
        self._glow.setColor(QColor("#6366F1"))
        self._glow.setOffset(0, 0)
        self.setGraphicsEffect(self._glow)

        self.anim = QPropertyAnimation(self._glow, b"blurRadius")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

    def set_input_widget(self, widget):
        self.input_layout.addWidget(widget)

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._glow.blurRadius())
        self.anim.setEndValue(15)
        self.anim.start()
        self.setStyleSheet("""
            QFrame#SettingCard {
                background: #252D3A;
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 16px;
            }
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._glow.blurRadius())
        self.anim.setEndValue(0)
        self.anim.start()
        self.setStyleSheet("""
            QFrame#SettingCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1E2430, stop:1 #161B22);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 16px;
            }
        """)
        super().leaveEvent(event)

class GeneralSettingsView(QWidget):
    def __init__(self):
        super().__init__()
        from config import config
        self.config = config
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 10, 25, 20)
        layout.setSpacing(20)
        
        # Header Row
        header_layout = QHBoxLayout()
        header = QLabel("General Settings")
        header.setStyleSheet("font-size: 26px; font-weight: bold; color: #f5e0dc;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        self.btn_reset = QPushButton("Reset to Defaults")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94A3B8;
                border: 1px solid #2D3748;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #F43F5E;
                border-color: #F43F5E;
                background-color: rgba(244, 63, 94, 0.05);
            }
        """)
        self.btn_reset.clicked.connect(self.reset_to_defaults)
        header_layout.addWidget(self.btn_reset)
        layout.addLayout(header_layout)
        
        # Scrollable Grid of Cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout(container)
        grid_layout.setContentsMargins(0, 5, 0, 10)
        grid_layout.setSpacing(20)
        
        icons_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons")
        
        # Section: Engine
        engine_header = QLabel("Tracking Engine")
        engine_header.setStyleSheet("color: #6366F1; font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; margin-top: 10px;")
        grid_layout.addWidget(engine_header, 0, 0, 1, 2)

        # Poll Interval Card
        self.card_poll = SettingCard(
            "Poll Interval", 
            "Determines how frequently the engine checks for the currently focused application window.",
            os.path.join(icons_path, "clock.svg")
        )
        self.in_poll = ModernSpinBox(1, 60, " s")
        self.in_poll.setValue(int(self.config.get("poll_interval")))
        self.card_poll.set_input_widget(self.in_poll)
        grid_layout.addWidget(self.card_poll, 1, 0)

        # Scan Interval Card
        self.card_scan = SettingCard(
            "Scan Interval", 
            "Frequency of background process scanning to detect application launches and exits.",
            os.path.join(icons_path, "bolt.svg")
        )
        self.in_scan = ModernSpinBox(5, 300, " s")
        self.in_scan.setValue(int(self.config.get("scan_interval")))
        self.card_scan.set_input_widget(self.in_scan)
        grid_layout.addWidget(self.card_scan, 1, 1)

        # Section: Maintenance
        maintenance_header = QLabel("Maintenance & Retention")
        maintenance_header.setStyleSheet("color: #6366F1; font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; margin-top: 25px;")
        grid_layout.addWidget(maintenance_header, 2, 0, 1, 2)

        # Idle Threshold Card
        self.card_idle = SettingCard(
            "Idle Threshold", 
            "The duration of inactivity before tracking is automatically paused to prevent over-counting.",
            os.path.join(icons_path, "settings.svg")
        )
        self.in_idle = ModernSpinBox(10, 3600, " s")
        self.in_idle.setValue(int(self.config.get("idle_threshold")))
        self.card_idle.set_input_widget(self.in_idle)
        grid_layout.addWidget(self.card_idle, 3, 0)

        # Data Retention Card
        self.card_retention = SettingCard(
            "Data Retention", 
            "Controls how many days of historical activity data should be kept in the local database.",
            os.path.join(icons_path, "analytics.svg")
        )
        self.in_retention = ModernSpinBox(1, 3650, " days")
        self.in_retention.setValue(int(self.config.get("data_retention_days")))
        self.card_retention.set_input_widget(self.in_retention)
        grid_layout.addWidget(self.card_retention, 3, 1)

        grid_layout.setRowStretch(4, 1)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Save Action
        save_container = QHBoxLayout()
        save_container.addStretch()
        
        self.btn_save = QPushButton("Apply All Changes")
        self.btn_save.setFixedSize(240, 48)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: 900;
                font-size: 14px;
                letter-spacing: 1px;
                text-transform: uppercase;
            }
            QPushButton:hover {
                background-color: #4F46E5;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: #4338CA;
            }
        """)
        self.btn_save.clicked.connect(self.save_settings)
        save_container.addWidget(self.btn_save)
        save_container.addStretch() # Center it!
        layout.addLayout(save_container)

    def save_settings(self):
        try:
            self.config.set("poll_interval", self.in_poll.value())
            self.config.set("idle_threshold", self.in_idle.value())
            self.config.set("scan_interval", self.in_scan.value())
            self.config.set("data_retention_days", self.in_retention.value())
            
            # Visual Feedback
            orig_text = self.btn_save.text()
            self.btn_save.setText("✓ Settings Applied")
            self.btn_save.setStyleSheet("""
                QPushButton {
                    background-color: #10B981;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-weight: 800;
                }
            """)
            QTimer.singleShot(2000, lambda: self.reset_save_button(orig_text))
        except Exception as e:
            self.btn_save.setText(f"Error: {e}")
            self.btn_save.setStyleSheet("background-color: #EF4444; color: white; border-radius: 12px;")

    def reset_save_button(self, text):
        self.btn_save.setText(text)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: 800;
                font-size: 14px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)

    def reset_to_defaults(self):
        from config import Config
        defaults = Config.DEFAULT_CONFIG
        self.in_poll.setValue(defaults["poll_interval"])
        self.in_idle.setValue(defaults["idle_threshold"])
        self.in_scan.setValue(defaults["scan_interval"])
        self.in_retention.setValue(defaults["data_retention_days"])
        
        # Flash the button to show something happened
        self.btn_reset.setText("Defaults Restored!")
        QTimer.singleShot(1500, lambda: self.btn_reset.setText("Reset to Defaults"))

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

class ExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 550)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main container with glassmorphic style
        self.container = QFrame()
        self.container.setObjectName("ExportContainer")
        self.container.setStyleSheet("""
            QFrame#ExportContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1E2430, stop:1 #161B22);
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 20px;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(20)
        
        # Header
        header_row = QHBoxLayout()
        title = QLabel("Export Data")
        title.setStyleSheet("color: white; font-size: 15pt; font-weight: 800;")
        header_row.addWidget(title)
        
        header_row.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                font-size: 12pt;
                border: none;
                border-radius: 15px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #F43F5E;
            }
        """)
        close_btn.clicked.connect(self.reject)
        header_row.addWidget(close_btn)
        container_layout.addLayout(header_row)
        
        # Date Range Section
        container_layout.addWidget(self.create_section_label("DATE RANGE"))
        
        date_layout = QHBoxLayout()
        
        from_col = QVBoxLayout()
        from_col.addWidget(QLabel("Start Date"))
        self.start_date = QDateEdit(QDate.currentDate().addDays(-7))
        self.start_date.setCalendarPopup(True)
        self.start_date.setStyleSheet(self.get_input_style())
        from_col.addWidget(self.start_date)
        date_layout.addLayout(from_col)
        
        to_col = QVBoxLayout()
        to_col.addWidget(QLabel("End Date"))
        self.end_date = QDateEdit(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setStyleSheet(self.get_input_style())
        to_col.addWidget(self.end_date)
        date_layout.addLayout(to_col)
        
        container_layout.addLayout(date_layout)
        
        # Export Format Section
        container_layout.addWidget(self.create_section_label("FORMAT"))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["CSV (Excel Compatible)", "JSON", "PDF Document"])
        self.format_combo.setStyleSheet(self.get_input_style())
        container_layout.addWidget(self.format_combo)
        
        # Data Category Section
        container_layout.addWidget(self.create_section_label("DATA CATEGORY"))
        
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Detailed Sessions", "Daily Usage Summary"])
        self.category_combo.setStyleSheet(self.get_input_style())
        container_layout.addWidget(self.category_combo)
        
        container_layout.addStretch()
        
        # Export Action
        self.btn_confirm = QPushButton("GENERATE EXPORT")
        self.btn_confirm.setFixedHeight(50)
        self.btn_confirm.setCursor(Qt.PointingHandCursor)
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: 900;
                font-size: 10pt;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
        """)
        self.btn_confirm.clicked.connect(self.perform_export)
        container_layout.addWidget(self.btn_confirm)
        
        layout.addWidget(self.container)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)

    def create_section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #6366F1; font-size: 8pt; font-weight: 900; letter-spacing: 1.5px;")
        return lbl

    def get_input_style(self):
        return """
            QDateEdit, QComboBox {
                background-color: #2D3748;
                border: 1px solid #4A5568;
                border-radius: 8px;
                padding: 10px;
                color: #CDD6F4;
                font-size: 10pt;
            }
            QDateEdit:focus, QComboBox:focus {
                border-color: #6366F1;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QDateEdit::drop-down {
                border: none;
                width: 30px;
            }
        """

    def perform_export(self):
        start = self.start_date.date().toPython().isoformat()
        end = self.end_date.date().toPython().isoformat()
        idx = self.format_combo.currentIndex()
        fmt = ["csv", "json", "pdf"][idx]
        cat = self.category_combo.currentIndex()
        
        file_filter = {
            "csv": "CSV Files (*.csv)",
            "json": "JSON Files (*.json)",
            "pdf": "PDF Files (*.pdf)"
        }[fmt]
        
        report_type = "Detailed_Sessions" if cat == 0 else "Daily_Usage_Summary"
        default_name = f"TimeForge_{report_type}_{start}_to_{end}.{fmt}"
        
        path, _ = QFileDialog.getSaveFileName(self, "Save Export File", default_name, file_filter)
        
        if not path:
            return
            
        try:
            if fmt == "pdf":
                self.generate_pdf(path, start, end, cat)
            else:
                if cat == 0: # Detailed Sessions
                    raw_data = database.get_sessions_range(start, end)
                    data = []
                    for d in raw_data:
                        start_dt = datetime.datetime.fromisoformat(d['start'])
                        end_dt = start_dt + datetime.timedelta(seconds=d['duration'])
                        data.append({
                            'app': d['app'],
                            'start_time': start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            'end_time': end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            'duration_seconds': d['duration'],
                            'duration_formatted': format_duration_pleasant(d['duration'])
                        })
                        
                    if fmt == "csv":
                        with open(path, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.DictWriter(f, fieldnames=['app', 'start_time', 'end_time', 'duration_seconds', 'duration_formatted'])
                            writer.writeheader()
                            writer.writerows(data)
                    else:
                        with open(path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=4)
                else: # Daily Summary
                    raw_data = database.get_usage_range(start, end)
                    data = []
                    for d in raw_data:
                        data.append({
                            'date': d['date'],
                            'app': d['app'],
                            'duration_seconds': d['duration'],
                            'duration_formatted': format_duration_pleasant(d['duration'])
                        })
                        
                    if fmt == "csv":
                        with open(path, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.DictWriter(f, fieldnames=['date', 'app', 'duration_seconds', 'duration_formatted'])
                            writer.writeheader()
                            writer.writerows(data)
                    else:
                        with open(path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=4)
            
            # Show success feedback
            self.btn_confirm.setText("✓ EXPORT SUCCESSFUL")
            self.btn_confirm.setStyleSheet("background-color: #10B981; color: white; border-radius: 12px; font-weight: 900;")
            QTimer.singleShot(2000, self.accept)
            
        except Exception as e:
            from main import logger
            logger.error(f"Export failed: {e}")
            self.btn_confirm.setText(f"ERROR: {str(e)[:20]}...")
            self.btn_confirm.setStyleSheet("background-color: #EF4444; color: white; border-radius: 12px;")

    def generate_pdf(self, path, start, end, cat):
        # Prepare data and logo
        icon_provider = QFileIconProvider()
        app_paths = database.get_app_paths()
        
        def get_icon_base64(app_name):
            exe_path = app_paths.get(app_name)
            if exe_path and os.path.exists(exe_path):
                icon = icon_provider.icon(QFileInfo(exe_path))
                pixmap = icon.pixmap(QSize(32, 32))
                buffer = QBuffer()
                buffer.open(QIODevice.WriteOnly)
                pixmap.save(buffer, "PNG")
                return base64.b64encode(buffer.data().data()).decode('utf-8')
            return ""

        logo_base64 = ""
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as image_file:
                logo_base64 = base64.b64encode(image_file.read()).decode('utf-8')

        start_dt_obj = datetime.date.fromisoformat(start)
        end_dt_obj = datetime.date.fromisoformat(end)
        date_range_str = start_dt_obj.strftime("%B %d, %Y") if start == end else f"{start_dt_obj.strftime('%b %d')} - {end_dt_obj.strftime('%b %d, %Y')}"

        if cat == 0:
            raw_data = database.get_sessions_range(start, end)
            title = "Detailed Activity Sessions"
            headers = ["", "Application", "Start Time", "End Time", "Duration"]
            col_widths = ["5%", "40%", "18%", "18%", "19%"]
            rows = []
            total_seconds = 0
            apps_seen = set()
            last_date = None
            
            for d in raw_data:
                start_dt = datetime.datetime.fromisoformat(d['start'])
                end_dt = start_dt + datetime.timedelta(seconds=d['duration'])
                
                date_str = start_dt.strftime("%Y-%m-%d")
                if date_str != last_date:
                    rows.append({
                        'html': f'<tr class="date-row"><td colspan="5" class="date-cell">{start_dt.strftime("%B %d, %Y")}</td></tr>'
                    })
                    last_date = date_str

                icon_b64 = get_icon_base64(d['app'])
                icon_img = f'<img src="data:image/png;base64,{icon_b64}" width="16" height="16">' if icon_b64 else ""
                
                display_name = d['app'][:-4].title() if d['app'].lower().endswith('.exe') else d['app'].title()
                total_seconds += d['duration']
                apps_seen.add(display_name)
                
                rows.append({
                    'data': [icon_img, display_name, start_dt.strftime("%H:%M:%S"), end_dt.strftime("%H:%M:%S"), format_duration_pleasant(d['duration'])],
                    'style': ""
                })
            
            summary_stats = [
                ("Total Time", format_duration_pleasant(total_seconds)),
                ("Apps Used", str(len(apps_seen))),
                ("Sessions", str(len(raw_data)))
            ]
        else:
            raw_data = database.get_usage_range(start, end)
            title = "Daily Usage Summary"
            headers = ["", "Application", "Duration"]
            col_widths = ["5%", "70%", "25%"]
            rows = []
            total_seconds = 0
            
            # For summary
            app_usage = {}
            last_date = None
            
            for d in raw_data:
                if d['date'] != last_date:
                    date_obj = datetime.date.fromisoformat(d['date'])
                    rows.append({
                        'html': f'<tr class="date-row"><td colspan="3" class="date-cell">{date_obj.strftime("%B %d, %Y")}</td></tr>'
                    })
                    last_date = d['date']

                icon_b64 = get_icon_base64(d['app'])
                icon_img = f'<img src="data:image/png;base64,{icon_b64}" width="16" height="16">' if icon_b64 else ""
                display_name = d['app'][:-4].title() if d['app'].lower().endswith('.exe') else d['app'].title()
                
                total_seconds += d['duration']
                app_usage[display_name] = app_usage.get(display_name, 0) + d['duration']
                
                rows.append({
                    'data': [icon_img, display_name, format_duration_pleasant(d['duration'])],
                    'style': ""
                })
            
            most_used = max(app_usage, key=app_usage.get) if app_usage else "N/A"
            summary_stats = [
                ("Total Usage", format_duration_pleasant(total_seconds)),
                ("Most Used", most_used),
                ("Entries", str(len(raw_data)))
            ]

        summary_html = "".join([f"""
            <div class="stat-card">
                <div class="stat-label">{label}</div>
                <div class="stat-value">{value}</div>
            </div>
        """ for label, value in summary_stats])

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, sans-serif; color: #1e293b; padding: 0 10pt 10pt 10pt; }}
                .header {{ text-align: center; margin-bottom: 15pt; border-bottom: 2pt solid #6366f1; padding-bottom: 15pt; }}
                h1 {{ color: #1e293b; margin: 0; font-size: 24pt; font-weight: bold; }}
                h2 {{ color: #6366f1; margin: 4pt 0 0 0; font-size: 14pt; text-transform: uppercase; letter-spacing: 1pt; }}
                
                .date-header {{ text-align: center; font-size: 12pt; font-weight: bold; color: #475569; margin-top: 15pt; margin-bottom: 10pt; text-transform: uppercase; letter-spacing: 0.5pt; }}
                
                .summary-container {{ margin-bottom: 20pt; text-align: center; width: 100%; }}
                .stat-card {{ display: inline-block; width: 30%; background-color: #f8fafc; border: 1pt solid #e2e8f0; padding: 10pt; margin: 0 1%; }}
                .stat-label {{ color: #64748b; font-size: 8pt; text-transform: uppercase; font-weight: bold; }}
                .stat-value {{ color: #6366f1; font-size: 14pt; font-weight: bold; margin-top: 2pt; }}

                table {{ width: 100%; border-collapse: collapse; margin-top: 10pt; table-layout: fixed; }}
                th {{ background-color: #f1f5f9; color: #475569; padding: 10pt 5pt; text-align: left; border-bottom: 1.5pt solid #cbd5e1; font-weight: bold; font-size: 9pt; text-transform: uppercase; }}
                td {{ padding: 10pt 5pt; border-bottom: 0.5pt solid #e2e8f0; font-size: 9pt; color: #334155; vertical-align: middle; }}
                .icon-col {{ text-align: center; }}
                
                .date-row {{ background-color: #f1f5f9; border-top: 2pt solid #6366f1; border-bottom: 1pt solid #cbd5e1; }}
                .date-cell {{ font-weight: bold; font-size: 11pt; color: #1e293b; padding: 8pt 10pt; text-align: left; }}
            </style>
        </head>
        <body>
            <div class="header">
                {f'<img src="data:image/png;base64,{logo_base64}" width="80" height="80" style="margin-bottom: 5pt;">' if logo_base64 else ''}
                <h1>TIME FORGE</h1>
                <h2>{title}</h2>
            </div>
            
            <div class="date-header">Report Period: {date_range_str}</div>
            
            <div class="summary-container">
                {summary_html}
            </div>
            
            <table>
                <thead>
                    <tr>
                        {"".join(f'<th width="{col_widths[i]}">{h if h else "&nbsp;"}</th>' for i, h in enumerate(headers))}
                    </tr>
                </thead>
                <tbody>
                    {"".join(r['html'] if 'html' in r else f"<tr{r['style']}><td class='icon-col'>{r['data'][0]}</td>{''.join(f'<td>{col}</td>' for col in r['data'][1:])}</tr>" for r in rows)}
                </tbody>
            </table>
            
            <div style="text-align: center; font-size: 8pt; color: #94a3b8; margin-top: 30pt; padding-top: 15pt; border-top: 0.5pt solid #e2e8f0;">
                Generated by <b>Time Forge Analytics</b> on {datetime.date.today().strftime("%B %d, %Y")}
            </div>
        </body>
        </html>
        """
        
        doc = QTextDocument()
        doc.setDefaultFont(QFont("Segoe UI", 10))
        doc.setHtml(html)
        
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageMargins(QMargins(15, 10, 15, 15), QPageLayout.Unit.Millimeter)
        
        doc.print_(printer)

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
        
        # Export Button
        self.btn_export = QPushButton("Export")
        self.btn_export.setFixedWidth(120)
        self.btn_export.setCursor(Qt.PointingHandCursor)
        
        icons_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons")
        export_icon = QIcon(os.path.join(icons_path, "export.svg"))
        self.btn_export.setIcon(export_icon)
        self.btn_export.setIconSize(QSize(18, 18))
        
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 15px;
                font-weight: 800;
                font-size: 13px;
                margin-left: 5px;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
        """)
        self.btn_export.clicked.connect(self.show_export_dialog)
        header_layout.addWidget(self.btn_export)
        
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

    def show_export_dialog(self):
        dialog = ExportDialog(self)
        dialog.exec()

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
            
            font_y = axis_y.labelsFont()
            font_y.setPointSize(8)
            axis_y.setLabelsFont(font_y)
            
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
        
        font_x = axis_x.labelsFont()
        font_x.setPointSize(8)
        axis_x.setLabelsFont(font_x)
        
        axis_x.setGridLineVisible(False)
        self.line_chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setRange(0, max(1, max_val * 1.2))
        axis_y.setTickCount(6)
        axis_y.setLabelFormat("%d m")
        axis_y.setLabelsColor(QColor("#CDD6F4"))
        
        font_y = axis_y.labelsFont()
        font_y.setPointSize(8)
        axis_y.setLabelsFont(font_y)
        
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
        self.drag_pos = None

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
        self.apps_view = TrackedAppsView()
        
        self.manage_view = AppManagementView()
        self.manage_view.apps_changed.connect(self.load_data)
        
        self.settings_view = GeneralSettingsView()

        self.stacked_widget.addWidget(self.summary_view)
        self.stacked_widget.addWidget(self.stats_view)
        self.stacked_widget.addWidget(self.apps_view)
        self.stacked_widget.addWidget(self.manage_view)
        self.stacked_widget.addWidget(self.settings_view)

        self.content_layout.addWidget(self.stacked_widget)
        container_layout.addWidget(content_widget)
        
        main_layout.addWidget(self.container)

        # Connect Sidebar Buttons
        self.sidebar.btn_home.clicked.connect(lambda: self.switch_view(0))
        self.sidebar.btn_stats.clicked.connect(lambda: self.switch_view(1))
        self.sidebar.btn_apps.clicked.connect(lambda: self.switch_view(2))
        self.sidebar.btn_manage.clicked.connect(lambda: self.switch_view(3))
        self.sidebar.btn_settings.clicked.connect(lambda: self.switch_view(4))
        
        # Initial View
        self.switch_view(0)


    def switch_view(self, index):
        self.stacked_widget.setCurrentIndex(index)
        self.sidebar.set_active_button(index)
        if index == 1:
            self.stats_view.refresh_data()
        elif index == 3:
            self.manage_view.load_tracked_apps()
            self.manage_view.search_input.setFocus()
        self.load_data()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drag_pos:
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

        # Update Apps View (Premium Grid)
        self.apps_view.update_apps(cleaned_data, active_sessions, focused, app_paths)
        
        # If stats view is visible, refresh it too
        if self.stacked_widget.currentIndex() == 1:
            self.stats_view.refresh_data()


    def refresh(self, focused_app=None, force=False):
        if focused_app is not None:
            self.current_focused_app = focused_app
            
        if not self.isVisible() and not force:
            return
            
        if self.sidebar.status_card.title.text() == "Tracking Error":
            self.sidebar.status_card.set_active(True, self.app_start_time)
            
        now = time.time()
        if not force and now - self.last_refresh_time < 1:
            return
            
        self.last_refresh_time = now
        self.load_data()

    def update_idle_status(self, is_idle):
        self.sidebar.status_card.set_active(not is_idle, self.app_start_time)

    def show_tracker_error(self, message):
        self.sidebar.status_card.set_error(message)
