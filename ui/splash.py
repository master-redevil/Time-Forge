import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect, QApplication
from PySide6.QtGui import QPixmap, QColor, QPainter, QPainterPath, QLinearGradient, QRadialGradient, QPen, QFont
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QParallelAnimationGroup, QRect, Property


class SplashScreen(QWidget):
    """Animated splash screen shown when the dashboard is opened from the system tray."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._callback = None
        self._bg_opacity = 0.0
        self._ring_angle = 0.0
        self._progress = 0.0
        self._glow_radius = 60.0

        self.setFixedSize(380, 420)
        self._center_on_screen()
        self._setup_ui()
        self._setup_animations()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(screen.left() + x, screen.top() + y)

    def _setup_ui(self):
        # Load logo
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
        self._logo_pixmap = None
        if os.path.exists(logo_path):
            self._logo_pixmap = QPixmap(logo_path).scaled(
                140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

    # ── Animated Properties ────────────────────────────────────────────

    @Property(float)
    def bg_opacity(self):
        return self._bg_opacity

    @bg_opacity.setter
    def bg_opacity(self, v):
        self._bg_opacity = v
        self.update()

    @Property(float)
    def ring_angle(self):
        return self._ring_angle

    @ring_angle.setter
    def ring_angle(self, v):
        self._ring_angle = v
        self.update()

    @Property(float)
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, v):
        self._progress = v
        self.update()

    @Property(float)
    def glow_radius(self):
        return self._glow_radius

    @glow_radius.setter
    def glow_radius(self, v):
        self._glow_radius = v
        self.update()

    # ── Animations ─────────────────────────────────────────────────────

    def _setup_animations(self):
        # Phase 1: Fade in background
        self._fade_in = QPropertyAnimation(self, b"bg_opacity")
        self._fade_in.setDuration(400)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)

        # Spinning ring
        self._ring_anim = QPropertyAnimation(self, b"ring_angle")
        self._ring_anim.setDuration(1800)
        self._ring_anim.setStartValue(0.0)
        self._ring_anim.setEndValue(360.0)
        self._ring_anim.setLoopCount(-1)
        self._ring_anim.setEasingCurve(QEasingCurve.Linear)

        # Progress bar fill
        self._progress_anim = QPropertyAnimation(self, b"progress")
        self._progress_anim.setDuration(1200)
        self._progress_anim.setStartValue(0.0)
        self._progress_anim.setEndValue(1.0)
        self._progress_anim.setEasingCurve(QEasingCurve.InOutQuad)

        # Glow pulse
        self._glow_anim = QPropertyAnimation(self, b"glow_radius")
        self._glow_anim.setDuration(1000)
        self._glow_anim.setStartValue(60.0)
        self._glow_anim.setEndValue(100.0)
        self._glow_anim.setEasingCurve(QEasingCurve.InOutSine)
        self._glow_anim.setLoopCount(-1)

        # Fade out
        self._fade_out = QPropertyAnimation(self, b"bg_opacity")
        self._fade_out.setDuration(350)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(self._on_fade_out_done)

    # ── Public API ─────────────────────────────────────────────────────

    def start(self, on_done_callback):
        """Show splash, run animations, then call `on_done_callback` when finished."""
        self._callback = on_done_callback
        self.show()
        self.raise_()

        # Start entrance animations
        self._fade_in.start()
        self._ring_anim.start()
        self._glow_anim.start()
        self._progress_anim.start()

        # After the progress completes, begin exit sequence
        self._progress_anim.finished.connect(self._begin_exit)

    def _begin_exit(self):
        self._ring_anim.stop()
        self._glow_anim.stop()

        # Short pause before fade out for visual polish
        QTimer.singleShot(150, self._do_fade_out)

    def _do_fade_out(self):
        self._fade_out.start()

    def _on_fade_out_done(self):
        self.hide()
        if self._callback:
            self._callback()
        self.close()

    # ── Painting ───────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2 - 20  # Shift center up a bit for balance

        opacity = self._bg_opacity

        # ── Background card ────────────────────────────────────────────
        card_path = QPainterPath()
        card_rect = QRect(0, 0, w, h)
        card_path.addRoundedRect(card_rect, 24, 24)

        # Dark gradient background
        bg_grad = QLinearGradient(0, 0, w, h)
        bg_grad.setColorAt(0.0, QColor(15, 17, 23, int(245 * opacity)))
        bg_grad.setColorAt(1.0, QColor(22, 27, 34, int(250 * opacity)))
        painter.fillPath(card_path, bg_grad)

        # Subtle border
        border_color = QColor(99, 102, 241, int(60 * opacity))
        painter.setPen(QPen(border_color, 1.5))
        painter.drawPath(card_path)

        if opacity < 0.05:
            painter.end()
            return

        # ── Radial glow behind logo ────────────────────────────────────
        glow = QRadialGradient(cx, cy, self._glow_radius)
        glow.setColorAt(0.0, QColor(99, 102, 241, int(50 * opacity)))
        glow.setColorAt(0.5, QColor(99, 102, 241, int(20 * opacity)))
        glow.setColorAt(1.0, QColor(99, 102, 241, 0))
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - int(self._glow_radius), cy - int(self._glow_radius),
                            int(self._glow_radius * 2), int(self._glow_radius * 2))

        # ── Spinning accent ring ───────────────────────────────────────
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._ring_angle)

        ring_radius = 85
        ring_pen = QPen(QColor(99, 102, 241, int(100 * opacity)), 2.5)
        ring_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(ring_pen)
        painter.drawArc(-ring_radius, -ring_radius,
                        ring_radius * 2, ring_radius * 2,
                        0 * 16, 90 * 16)  # Quarter arc

        # Second subtle arc segment
        ring_pen2 = QPen(QColor(139, 92, 246, int(50 * opacity)), 1.5)
        ring_pen2.setCapStyle(Qt.RoundCap)
        painter.setPen(ring_pen2)
        painter.drawArc(-ring_radius, -ring_radius,
                        ring_radius * 2, ring_radius * 2,
                        180 * 16, 60 * 16)

        painter.restore()

        # ── Logo ───────────────────────────────────────────────────────
        if self._logo_pixmap:
            painter.setOpacity(opacity)
            lx = cx - self._logo_pixmap.width() // 2
            ly = cy - self._logo_pixmap.height() // 2
            painter.drawPixmap(lx, ly, self._logo_pixmap)
            painter.setOpacity(1.0)

        # ── App name text ──────────────────────────────────────────────
        painter.setOpacity(opacity)
        title_font = QFont("Inter", 18, QFont.Bold)
        title_font.setLetterSpacing(QFont.AbsoluteSpacing, 3.0)
        painter.setFont(title_font)
        painter.setPen(QColor(205, 214, 244, int(230 * opacity)))
        painter.drawText(QRect(0, cy + 95, w, 30), Qt.AlignCenter, "TIME FORGE")

        # Subtitle
        sub_font = QFont("Inter", 10)
        sub_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        painter.setFont(sub_font)
        painter.setPen(QColor(148, 163, 184, int(180 * opacity)))
        painter.drawText(QRect(0, cy + 125, w, 20), Qt.AlignCenter, "Productivity Tracker")

        # ── Progress bar ───────────────────────────────────────────────
        bar_y = cy + 165
        bar_w = 200
        bar_h = 3
        bar_x = (w - bar_w) // 2

        # Track
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(45, 55, 72, int(180 * opacity)))
        track_path = QPainterPath()
        track_path.addRoundedRect(bar_x, bar_y, bar_w, bar_h, 1.5, 1.5)
        painter.drawPath(track_path)

        # Fill
        fill_w = int(bar_w * self._progress)
        if fill_w > 0:
            fill_grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            fill_grad.setColorAt(0.0, QColor(99, 102, 241, int(255 * opacity)))
            fill_grad.setColorAt(1.0, QColor(139, 92, 246, int(255 * opacity)))
            painter.setBrush(fill_grad)
            fill_path = QPainterPath()
            fill_path.addRoundedRect(bar_x, bar_y, fill_w, bar_h, 1.5, 1.5)
            painter.drawPath(fill_path)

        painter.setOpacity(1.0)
        painter.end()
