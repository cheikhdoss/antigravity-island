import math
import ctypes
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QRadialGradient, QPainterPath

class PointerOverlay(QWidget):
    """
    Calque de surbrillance et pointeur laser virtuel pour Antigravity.
    Inspiré de HeyClicky : permet à Antigravity de désigner visuellement
    un élément à l'écran avec une animation d'ondes radar et une étiquette.
    Totalement transparent aux clics de souris (WindowTransparentForInput).
    """

    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.target_x = 0.0
        self.target_y = 0.0
        self.label = ""
        self.color = QColor(56, 189, 248)  # Cyan par défaut
        self.anim_phase = 0.0
        self.opacity = 0.0
        self.lifetime = 0.0
        self.max_lifetime = 3.5

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)

    def point_at(self, x: float, y: float, label: str = "", duration: float = 3.5, color: str = None):
        """Active le pointeur laser à la position (x, y) de l'écran avec étiquette."""
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.virtualGeometry())

        self.target_x = float(x)
        self.target_y = float(y)
        self.label = label
        if color:
            self.color = QColor(color)
        else:
            self.color = QColor(56, 189, 248)

        self.anim_phase = 0.0
        self.opacity = 1.0
        self.lifetime = 0.0
        self.max_lifetime = duration

        if not self.timer.isActive():
            self.timer.start(16)  # 60 FPS

        self.show()
        
        # Renforcer le maintien au premier plan absolu (HWND_TOPMOST)
        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        SWP_SHOWWINDOW = 0x0040
        try:
            ctypes.windll.user32.SetWindowPos(int(self.winId()), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
        except Exception:
            pass

        self.update()

    def _on_tick(self):
        self.anim_phase = (self.anim_phase + 0.06) % (2.0 * math.pi)
        self.lifetime += 0.016

        # Fondu doux en fin de vie
        remaining = self.max_lifetime - self.lifetime
        if remaining < 0.6:
            self.opacity = max(0.0, remaining / 0.6)
        else:
            self.opacity = 1.0

        if self.lifetime >= self.max_lifetime:
            self.timer.stop()
            self.hide()

        self.update()

    def paintEvent(self, event):
        if self.opacity <= 0.01:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        cx = self.target_x
        cy = self.target_y

        # 1. Anneaux d'onde radar pulsants
        for i in range(2):
            ring_progress = (self.anim_phase / (2.0 * math.pi) + (i * 0.5)) % 1.0
            r = 10.0 + ring_progress * 38.0
            alpha = int(220 * (1.0 - ring_progress) * self.opacity)
            
            c_ring = QColor(self.color)
            c_ring.setAlpha(max(0, min(255, alpha)))
            pen = QPen(c_ring, 1.8)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), r, r)

        # 2. Halo lumineux central
        glow = QRadialGradient(QPointF(cx, cy), 16.0)
        c_glow = QColor(self.color)
        c_glow.setAlpha(int(180 * self.opacity))
        glow.setColorAt(0.0, c_glow)
        c_zero = QColor(self.color)
        c_zero.setAlpha(0)
        glow.setColorAt(1.0, c_zero)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPointF(cx, cy), 16.0, 16.0)

        # 3. Point laser central
        c_dot = QColor(255, 255, 255)
        c_dot.setAlpha(int(255 * self.opacity))
        painter.setBrush(QBrush(c_dot))
        painter.drawEllipse(QPointF(cx, cy), 3.5, 3.5)

        # 4. Étiquette textuelle (Badge d'indication)
        if self.label:
            font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            text_w = metrics.horizontalAdvance(self.label)
            text_h = metrics.height()

            badge_w = text_w + 20.0
            badge_h = text_h + 10.0
            badge_x = cx - badge_w / 2.0
            badge_y = cy - 42.0 - badge_h

            # Empêcher de sortir de l'écran en haut
            if badge_y < 10:
                badge_y = cy + 24.0

            badge_rect = QRectF(badge_x, badge_y, badge_w, badge_h)
            
            # Fond verre fumé
            bg_badge = QColor(15, 23, 42, int(230 * self.opacity))
            painter.setBrush(QBrush(bg_badge))
            pen_badge = QPen(QColor(self.color.red(), self.color.green(), self.color.blue(), int(180 * self.opacity)), 1.0)
            painter.setPen(pen_badge)
            painter.drawRoundedRect(badge_rect, 6.0, 6.0)

            # Texte
            c_txt = QColor(255, 255, 255, int(250 * self.opacity))
            painter.setPen(c_txt)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self.label)
