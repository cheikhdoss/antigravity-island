import math
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QBrush, QPen

class GlowingOrb:
    """Orbe lumineux pulsant avec anneau rotatif pour l'état d'analyse et réflexion."""
    
    def __init__(self):
        self.angle = 0.0
        self.pulse = 0.0

    def update(self, delta: float = 0.05):
        self.angle = (self.angle + delta * 120.0) % 360.0
        self.pulse = (math.sin(self.angle * math.pi / 90.0) + 1.0) * 0.5

    def draw(self, painter: QPainter, center_x: float, center_y: float, radius: float = 10.0):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        center = QPointF(center_x, center_y)
        dynamic_r = radius + self.pulse * 2.5

        # 1. Halo extérieur doux
        glow = QRadialGradient(center, dynamic_r * 2.2)
        c_glow = QColor(168, 85, 247, int(80 + self.pulse * 60))
        glow.setColorAt(0.0, c_glow)
        glow.setColorAt(1.0, QColor(168, 85, 247, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(center, dynamic_r * 2.2, dynamic_r * 2.2)

        # 2. Noyau brillant
        core = QRadialGradient(center, dynamic_r)
        core.setColorAt(0.0, QColor(255, 255, 255, 240))
        core.setColorAt(0.6, QColor(192, 132, 252, 200))
        core.setColorAt(1.0, QColor(147, 51, 234, 160))
        painter.setBrush(QBrush(core))
        painter.drawEllipse(center, dynamic_r, dynamic_r)

        # 3. Anneau orbital
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(QColor(230, 200, 255, 180), 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        span_angle = int(120 * 16)
        start_angle = int(self.angle * 16)
        rect = QPointF(center_x - dynamic_r * 1.5, center_y - dynamic_r * 1.5)
        painter.drawArc(
            int(rect.x()), int(rect.y()),
            int(dynamic_r * 3.0), int(dynamic_r * 3.0),
            start_angle, span_angle
        )

        painter.restore()
