import math
import random
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QLinearGradient

class WaveformVisualizer:
    """Générateur de barres d'ondes audio animées réactives pour l'état d'écoute et de parole."""
    
    def __init__(self, bar_count: int = 7):
        self.bar_count = bar_count
        self.phase = 0.0
        self.target_levels = [0.2] * bar_count
        self.current_levels = [0.2] * bar_count
        self.bar_width = 3.5
        self.bar_spacing = 3.0

    def update(self, delta: float = 0.05, audio_power: float = 0.0):
        """Met à jour les hauteurs des barres selon le temps et le volume audio."""
        self.phase += delta * 4.0
        for i in range(self.bar_count):
            # Simulation fluide basée sur sinusoïdes harmoniques + volume
            sine_val = (math.sin(self.phase + i * 0.8) + 1.0) * 0.5
            noise = random.uniform(-0.1, 0.1)
            intensity = max(0.15, min(1.0, sine_val * 0.7 + audio_power * 0.8 + noise))
            self.target_levels[i] = intensity
            # Interpolation douce (lerp)
            self.current_levels[i] += (self.target_levels[i] - self.current_levels[i]) * 0.35

    def draw(self, painter: QPainter, center_x: float, center_y: float, max_height: float, color: QColor):
        """Dessine les barres centrées verticalement."""
        total_width = self.bar_count * self.bar_width + (self.bar_count - 1) * self.bar_spacing
        start_x = center_x - total_width / 2.0

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(self.bar_count):
            bar_h = max(4.0, self.current_levels[i] * max_height)
            bx = start_x + i * (self.bar_width + self.bar_spacing)
            by = center_y - bar_h / 2.0
            
            # Dégradé vertical pour chaque barre
            grad = QLinearGradient(bx, by, bx, by + bar_h)
            c1 = QColor(color)
            c1.setAlpha(240)
            c2 = QColor(color)
            c2.setAlpha(120)
            grad.setColorAt(0.0, c1)
            grad.setColorAt(1.0, c2)
            
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRectF(bx, by, self.bar_width, bar_h), self.bar_width / 2.0, self.bar_width / 2.0)

        painter.restore()
