import sys
import math
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QTimer, QVariantAnimation, QEasingCurve, pyqtSignal
)
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QPainterPath, QRadialGradient
)

from island.config import Config
from island.components.waveform import WaveformVisualizer
from island.components.glowing_orb import GlowingOrb

class IslandWindow(QWidget):
    """
    Fenêtre principale de l'encoche dynamique Antigravity.
    Collée au plus près du bord supérieur de l'écran Windows, sans bordure et ultra-fluide.
    """
    
    # Signal thread-safe pour les ordres venant du WebSocket
    state_change_requested = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()
        
        # Configuration des flags de fenêtre Windows
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # État courant
        self.current_state = "idle"
        cfg = Config.STATES[self.current_state]
        
        # Dimensions personnalisables
        self.custom_idle_w = 110.0
        self.custom_idle_h = 30.0
        
        self.cur_w = float(self.custom_idle_w)
        self.cur_h = float(self.custom_idle_h)
        self.cur_r = float(self.custom_idle_h / 2.0)
        self.target_w = self.cur_w
        self.target_h = self.cur_h
        self.target_r = self.cur_r

        # Paramètres de disposition
        self.position_mode = "notch"   # "notch" (collé au header à Y=0) ou "floating"
        self.alignment = "center"       # "center", "left", "right"
        self.top_margin = 0            # 0px pour collage absolu
        self.accent_color = Config.COLOR_ACCENT_CYAN

        # Contenu dynamique
        self.message_text = "Je suis prêt."
        self.action_title = "Prêt"
        self.action_detail = ""
        self.progress_value = 0.0

        # Composants visuels animés
        self.waveform = WaveformVisualizer(bar_count=9)
        self.orb = GlowingOrb()
        self.audio_power = 0.0
        self.idle_pulse = 0.0

        # Animation de morphing fluide
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(350)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.valueChanged.connect(self._on_anim_step)

        # Timer de rendu à 60 FPS
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self._on_tick)
        self.render_timer.start(16)

        # Connexion du signal pour les commandes distantes
        self.state_change_requested.connect(self.apply_remote_command)

        # Positionnement initial
        self._update_geometry()

    def apply_settings(self, settings: dict):
        """Applique les réglages personnalisés (couleur, position, taille)."""
        if "accent_color" in settings:
            self.accent_color = QColor(settings["accent_color"])
        if "position_mode" in settings:
            self.position_mode = settings["position_mode"]
            self.top_margin = 0 if self.position_mode == "notch" else 12
        if "alignment" in settings:
            self.alignment = settings["alignment"]
        if "idle_width" in settings:
            self.custom_idle_w = float(settings["idle_width"])
        if "idle_height" in settings:
            self.custom_idle_h = float(settings["idle_height"])
        if "island_visible" in settings:
            if settings["island_visible"]:
                self.show()
            else:
                self.hide()

        # Si on est en mode idle, mettre à jour immédiatement les dimensions cibles
        if self.current_state == "idle":
            self.cur_w = self.custom_idle_w
            self.cur_h = self.custom_idle_h
            self.cur_r = self.custom_idle_h / 2.0
            self.target_w = self.cur_w
            self.target_h = self.cur_h
            self.target_r = self.cur_r

        self._update_geometry()
        self.update()

    def set_state(self, state_name: str, payload: dict = None):
        """Bascule d'un état à un autre avec animation morphique."""
        if state_name not in Config.STATES:
            return
            
        self.current_state = state_name
        
        if payload:
            if "text" in payload:
                self.message_text = payload["text"]
            if "title" in payload:
                self.action_title = payload["title"]
            if "detail" in payload:
                self.action_detail = payload["detail"]
            if "progress" in payload:
                self.progress_value = float(payload["progress"])

        self.anim.stop()
        self.start_w = self.cur_w
        self.start_h = self.cur_h
        self.start_r = self.cur_r
        
        if state_name == "idle":
            self.target_w = float(self.custom_idle_w)
            self.target_h = float(self.custom_idle_h)
            self.target_r = float(self.custom_idle_h / 2.0)
        else:
            target_cfg = Config.STATES[state_name]
            self.target_w = float(target_cfg.width)
            self.target_h = float(target_cfg.height)
            self.target_r = float(target_cfg.radius)
        
        if state_name in ["speaking", "action"]:
            self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim.setDuration(380)
        else:
            self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
            self.anim.setDuration(300)
            
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def _on_anim_step(self, progress: float):
        self.cur_w = self.start_w + (self.target_w - self.start_w) * progress
        self.cur_h = self.start_h + (self.target_h - self.start_h) * progress
        self.cur_r = self.start_r + (self.target_r - self.start_r) * progress
        self._update_geometry()
        self.update()

    def _update_geometry(self):
        """Recalcule et aligne la fenêtre contre le bord supérieur de l'écran."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        screen_geo = screen.geometry()
        
        pad_x = Config.SHADOW_BLUR
        pad_top = 0 if self.position_mode == "notch" else Config.SHADOW_BLUR
        
        total_w = int(self.cur_w + pad_x * 2)
        total_h = int(self.cur_h + pad_top + Config.SHADOW_BLUR + Config.SHADOW_OFFSET_Y)
        
        # Calcul du X selon l'alignement
        if self.alignment == "left":
            x = screen_geo.x() + 40
        elif self.alignment == "right":
            x = screen_geo.x() + screen_geo.width() - total_w - 40
        else:  # "center"
            x = screen_geo.x() + (screen_geo.width() - total_w) // 2

        # Calcul du Y collé le plus possible au header
        if self.position_mode == "notch":
            y = screen_geo.y()  # Collé à 0px
        else:
            y = screen_geo.y() + self.top_margin
        
        self.setGeometry(x, y, total_w, total_h)

    def _on_tick(self):
        if self.current_state in ["listening", "speaking"]:
            self.waveform.update(delta=0.04, audio_power=self.audio_power)
        elif self.current_state == "thinking":
            self.orb.update(delta=0.04)

        self.update()

    def apply_remote_command(self, action: str, data: dict):
        if action == "set_state":
            state = data.get("state", "idle")
            self.set_state(state, data)
        elif action == "speak":
            self.message_text = data.get("text", "")
            self.set_state("speaking", data)
        elif action == "audio_power":
            self.audio_power = float(data.get("power", 0.0))
        elif action == "action":
            self.set_state("action", data)
        elif action == "idle":
            self.set_state("idle", data)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            states_order = ["idle", "listening", "thinking", "speaking", "action"]
            idx = states_order.index(self.current_state)
            next_state = states_order[(idx + 1) % len(states_order)]
            self.set_state(next_state)
        elif event.button() == Qt.MouseButton.RightButton:
            self.set_state("idle")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        pad_x = Config.SHADOW_BLUR
        pad_top = 0.0 if self.position_mode == "notch" else float(Config.SHADOW_BLUR)
        
        pill_rect = QRectF(pad_x, pad_top, self.cur_w, self.cur_h)
        radius = min(self.cur_r, self.cur_h / 2.0)

        # 1. Ombre portée douce (Drop Shadow sous l'encoche)
        shadow_path = QPainterPath()
        if self.position_mode == "notch":
            # Ombre uniquement vers le bas et sur les côtés
            shadow_rect = pill_rect.adjusted(-2, 0, 2, 8)
            shadow_path.addRoundedRect(shadow_rect, radius, radius)
        else:
            shadow_rect = pill_rect.adjusted(-2, 2, 2, 6)
            shadow_path.addRoundedRect(shadow_rect, radius + 2, radius + 2)
        
        shadow_color = QColor(Config.COLOR_SHADOW)
        painter.fillPath(shadow_path, QBrush(shadow_color))

        # 2. Corps de l'encoche (Obsidian Black Glass)
        pill_path = QPainterPath()
        if self.position_mode == "notch":
            # Coins inférieurs arrondis, bord supérieur collé parfaitement
            pill_path.addRoundedRect(pill_rect, radius, radius)
        else:
            pill_path.addRoundedRect(pill_rect, radius, radius)

        bg_grad = QLinearGradient(pill_rect.topLeft(), pill_rect.bottomLeft())
        bg_grad.setColorAt(0.0, QColor(14, 14, 18, 252))
        bg_grad.setColorAt(1.0, QColor(6, 6, 8, 255))
        
        painter.fillPath(pill_path, QBrush(bg_grad))

        # 3. Bordure subtile Hairline (1px)
        border_pen = QPen(Config.COLOR_BORDER, 1.0)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(pill_path)

        # 4. Rendu des contenus selon l'état
        if self.current_state == "idle":
            self._draw_idle_content(painter, pill_rect)
        elif self.current_state == "listening":
            self._draw_listening_content(painter, pill_rect)
        elif self.current_state == "thinking":
            self._draw_thinking_content(painter, pill_rect)
        elif self.current_state == "speaking":
            self._draw_speaking_content(painter, pill_rect)
        elif self.current_state == "action":
            self._draw_action_content(painter, pill_rect)

    def _draw_idle_content(self, painter: QPainter, rect: QRectF):
        """Contenu compact au repos — Épuré, sans aucun texte (Pure Apple Pill)."""
        center = rect.center()
        acc = getattr(self, "accent_color", Config.COLOR_ACCENT_CYAN)
        
        # Halo lumineux doux
        glow = QRadialGradient(center, 9.0)
        c_glow = QColor(acc)
        c_glow.setAlpha(180)
        glow.setColorAt(0.0, c_glow)
        c_glow_zero = QColor(acc)
        c_glow_zero.setAlpha(0)
        glow.setColorAt(1.0, c_glow_zero)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(center, 9.0, 9.0)

        # Pastille centrale compacte
        painter.setBrush(QBrush(acc))
        painter.drawEllipse(center, 3.2, 3.2)

    def _draw_listening_content(self, painter: QPainter, rect: QRectF):
        cy = rect.center().y()
        dot_x = rect.left() + 22.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(Config.COLOR_ACCENT_GREEN))
        painter.drawEllipse(QPointF(dot_x, cy), 4.0, 4.0)

        painter.setPen(Config.COLOR_TEXT_PRIMARY)
        font = QFont("Segoe UI", 9, QFont.Weight.Medium)
        painter.setFont(font)
        text_rect = QRectF(dot_x + 14.0, rect.top(), 160.0, rect.height())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "À votre écoute...")

        wave_cx = rect.right() - 46.0
        self.waveform.draw(painter, wave_cx, cy, max_height=22.0, color=Config.COLOR_ACCENT_GREEN)

    def _draw_thinking_content(self, painter: QPainter, rect: QRectF):
        cy = rect.center().y()
        orb_x = rect.left() + 26.0
        self.orb.draw(painter, orb_x, cy, radius=6.5)

        painter.setPen(Config.COLOR_TEXT_PRIMARY)
        font = QFont("Segoe UI", 9, QFont.Weight.Medium)
        painter.setFont(font)
        text_rect = QRectF(orb_x + 18.0, rect.top(), rect.width() - 50.0, rect.height())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Analyse en cours...")

    def _draw_speaking_content(self, painter: QPainter, rect: QRectF):
        header_y = rect.top() + 16.0
        dot_x = rect.left() + 24.0
        
        acc = getattr(self, "accent_color", Config.COLOR_ACCENT_CYAN)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(acc))
        painter.drawEllipse(QPointF(dot_x, header_y), 4.0, 4.0)

        painter.setPen(Config.COLOR_TEXT_SECONDARY)
        font_header = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
        painter.setFont(font_header)
        painter.drawText(
            QRectF(dot_x + 12.0, header_y - 8.0, 200.0, 16.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "RÉPONSE D'ANTIGRAVITY"
        )

        wave_cx = rect.right() - 40.0
        self.waveform.draw(painter, wave_cx, header_y, max_height=14.0, color=acc)

        painter.setPen(Config.COLOR_TEXT_PRIMARY)
        font_msg = QFont("Segoe UI", 10, QFont.Weight.Normal)
        painter.setFont(font_msg)
        
        msg_rect = QRectF(rect.left() + 24.0, header_y + 12.0, rect.width() - 48.0, rect.height() - header_y - 8.0)
        painter.drawText(
            msg_rect,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
            self.message_text
        )

    def _draw_action_content(self, painter: QPainter, rect: QRectF):
        top_y = rect.top() + 16.0
        dot_x = rect.left() + 24.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(Config.COLOR_ACCENT_ORANGE))
        painter.drawEllipse(QPointF(dot_x, top_y), 4.0, 4.0)

        painter.setPen(Config.COLOR_TEXT_SECONDARY)
        font_header = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
        painter.setFont(font_header)
        painter.drawText(
            QRectF(dot_x + 12.0, top_y - 8.0, 250.0, 16.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "ACTION EN COURS"
        )

        painter.setPen(Config.COLOR_TEXT_PRIMARY)
        font_title = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
        painter.setFont(font_title)
        painter.drawText(
            QRectF(rect.left() + 24.0, top_y + 12.0, rect.width() - 48.0, 22.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.action_title
        )

        painter.setPen(Config.COLOR_TEXT_SECONDARY)
        font_detail = QFont("Segoe UI", 9, QFont.Weight.Normal)
        painter.setFont(font_detail)
        painter.drawText(
            QRectF(rect.left() + 24.0, top_y + 36.0, rect.width() - 48.0, 20.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.action_detail or "Exécution des sous-tâches..."
        )

        bar_w = rect.width() - 48.0
        bar_h = 3.5
        bar_x = rect.left() + 24.0
        bar_y = rect.bottom() - 20.0
        
        painter.setBrush(QBrush(QColor(255, 255, 255, 20)))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2.0, 2.0)
        
        active_w = max(4.0, bar_w * min(1.0, max(0.05, self.progress_value)))
        painter.setBrush(QBrush(Config.COLOR_ACCENT_ORANGE))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, active_w, bar_h), 2.0, 2.0)
