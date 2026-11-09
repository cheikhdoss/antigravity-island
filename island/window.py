import sys
import math
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QTimer, QVariantAnimation, QEasingCurve, pyqtSignal
)
from PyQt6.QtWidgets import QWidget, QApplication, QGraphicsDropShadowEffect
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QPainterPath, QRadialGradient
)

from island.config import Config
from island.components.waveform import WaveformVisualizer
from island.components.glowing_orb import GlowingOrb

class IslandWindow(QWidget):
    """
    Fenêtre principale de l'encoche dynamique Antigravity.
    Toujours au premier plan, sans bordure, transparente et centrée en haut de l'écran.
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
        
        self.cur_w = float(cfg.width)
        self.cur_h = float(cfg.height)
        self.cur_r = float(cfg.radius)
        self.target_w = self.cur_w
        self.target_h = self.cur_h
        self.target_r = self.cur_r

        # Contenu dynamique
        self.message_text = "Bonjour ! Je suis Antigravity."
        self.action_title = "Prêt"
        self.action_detail = ""
        self.progress_value = 0.0

        # Composants visuels animés
        self.waveform = WaveformVisualizer(bar_count=9)
        self.orb = GlowingOrb()
        self.audio_power = 0.0
        self.idle_pulse = 0.0

        # Animation de morphing
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(350)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.valueChanged.connect(self._on_anim_step)

        # Timer de rendu à 60 FPS pour les composants vivants
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self._on_tick)
        self.render_timer.start(16)  # ~60 FPS

        # Connexion du signal pour les commandes distantes
        self.state_change_requested.connect(self.apply_remote_command)

        # Positionnement initial
        self._update_geometry()

    def set_state(self, state_name: str, payload: dict = None):
        """Bascule d'un état à un autre avec animation fluide."""
        if state_name not in Config.STATES:
            print(f"⚠️ État inconnu : {state_name}")
            return
            
        self.current_state = state_name
        target_cfg = Config.STATES[state_name]
        
        if payload:
            if "text" in payload:
                self.message_text = payload["text"]
            if "title" in payload:
                self.action_title = payload["title"]
            if "detail" in payload:
                self.action_detail = payload["detail"]
            if "progress" in payload:
                self.progress_value = float(payload["progress"])

        # Lancer l'animation de morphing
        self.anim.stop()
        self.start_w = self.cur_w
        self.start_h = self.cur_h
        self.start_r = self.cur_r
        
        self.target_w = float(target_cfg.width)
        self.target_h = float(target_cfg.height)
        self.target_r = float(target_cfg.radius)
        
        # Courbe d'interpolation souple
        if state_name in ["speaking", "action"]:
            self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim.setDuration(400)
        else:
            self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
            self.anim.setDuration(320)
            
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def _on_anim_step(self, progress: float):
        """Met à jour les dimensions en cours d'animation."""
        self.cur_w = self.start_w + (self.target_w - self.start_w) * progress
        self.cur_h = self.start_h + (self.target_h - self.start_h) * progress
        self.cur_r = self.start_r + (self.target_r - self.start_r) * progress
        self._update_geometry()
        self.update()

    def _update_geometry(self):
        """Recalcule et centre la fenêtre sur l'écran principal."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        screen_geo = screen.geometry()
        
        # Marge de padding pour l'ombre portée
        padding = Config.SHADOW_BLUR * 2
        total_w = int(self.cur_w + padding)
        total_h = int(self.cur_h + padding + Config.SHADOW_OFFSET_Y)
        
        x = screen_geo.x() + (screen_geo.width() - total_w) // 2
        y = screen_geo.y() + Config.TOP_MARGIN
        
        self.setGeometry(x, y, total_w, total_h)

    def _on_tick(self):
        """Boucle de mise à jour des éléments dynamiques (waveform, orb, etc.)."""
        # Mise à jour des animations internes
        self.idle_pulse = (math.sin(QApplication.instance().applicationPid() + self.render_timer.remainingTime() * 0.05) + 1.0) * 0.5
        
        if self.current_state in ["listening", "speaking"]:
            self.waveform.update(delta=0.04, audio_power=self.audio_power)
        elif self.current_state == "thinking":
            self.orb.update(delta=0.04)

        self.update()

    def apply_remote_command(self, action: str, data: dict):
        """Applique une commande reçue depuis le WebSocket d'Antigravity."""
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
        """Permet de cliquer pour cycler entre les états lors du test manuel."""
        if event.button() == Qt.MouseButton.LeftButton:
            states_order = ["idle", "listening", "thinking", "speaking", "action"]
            idx = states_order.index(self.current_state)
            next_state = states_order[(idx + 1) % len(states_order)]
            self.set_state(next_state)
        elif event.button() == Qt.MouseButton.RightButton:
            # Revenir à idle
            self.set_state("idle")

    def paintEvent(self, event):
        """Rendu vectoriel ultra-soigné de l'encoche."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        pad = Config.SHADOW_BLUR
        pill_rect = QRectF(pad, pad, self.cur_w, self.cur_h)
        radius = min(self.cur_r, self.cur_h / 2.0)

        # 1. Ombre portée douce (Drop Shadow)
        shadow_path = QPainterPath()
        shadow_rect = pill_rect.adjusted(-2, 2, 2, 6)
        shadow_path.addRoundedRect(shadow_rect, radius + 2, radius + 2)
        
        shadow_color = QColor(Config.COLOR_SHADOW)
        painter.fillPath(shadow_path, QBrush(shadow_color))

        # 2. Corps de l'encoche (Obsidian Black Glass)
        pill_path = QPainterPath()
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
        """Contenu compact au repos."""
        # Point lumineux Antigravity Cyan
        cy = rect.center().y()
        dot_x = rect.left() + 20.0
        
        # Halo cyan
        glow = QRadialGradient(QPointF(dot_x, cy), 8.0)
        glow.setColorAt(0.0, QColor(56, 189, 248, 220))
        glow.setColorAt(1.0, QColor(56, 189, 248, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPointF(dot_x, cy), 8.0, 8.0)

        # Point solide
        painter.setBrush(QBrush(QColor(56, 189, 248)))
        painter.drawEllipse(QPointF(dot_x, cy), 3.5, 3.5)

        # Label discret
        painter.setPen(Config.COLOR_TEXT_PRIMARY)
        font = QFont("Segoe UI", 9, QFont.Weight.Medium)
        painter.setFont(font)
        text_rect = QRectF(dot_x + 12.0, rect.top(), rect.width() - 35.0, rect.height())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Antigravity")

    def _draw_listening_content(self, painter: QPainter, rect: QRectF):
        """Contenu étendu avec onde sonore active."""
        cy = rect.center().y()
        
        # Icône Micro / Pastille verte pulsante
        dot_x = rect.left() + 22.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(Config.COLOR_ACCENT_GREEN))
        painter.drawEllipse(QPointF(dot_x, cy), 4.0, 4.0)

        # Texte
        painter.setPen(Config.COLOR_TEXT_PRIMARY)
        font = QFont("Segoe UI", 9, QFont.Weight.Medium)
        painter.setFont(font)
        text_rect = QRectF(dot_x + 14.0, rect.top(), 160.0, rect.height())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "À votre écoute...")

        # Visualiseur d'onde sonore
        wave_cx = rect.right() - 46.0
        self.waveform.draw(painter, wave_cx, cy, max_height=22.0, color=Config.COLOR_ACCENT_GREEN)

    def _draw_thinking_content(self, painter: QPainter, rect: QRectF):
        """Contenu avec orbe de réflexion."""
        cy = rect.center().y()
        
        # Orbe rotatif violet
        orb_x = rect.left() + 26.0
        self.orb.draw(painter, orb_x, cy, radius=6.5)

        # Texte
        painter.setPen(Config.COLOR_TEXT_PRIMARY)
        font = QFont("Segoe UI", 9, QFont.Weight.Medium)
        painter.setFont(font)
        text_rect = QRectF(orb_x + 18.0, rect.top(), rect.width() - 50.0, rect.height())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Analyse en cours...")

    def _draw_speaking_content(self, painter: QPainter, rect: QRectF):
        """Contenu élargi affichant le message de l'agent."""
        # En-tête
        header_y = rect.top() + 16.0
        dot_x = rect.left() + 24.0
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(Config.COLOR_ACCENT_CYAN))
        painter.drawEllipse(QPointF(dot_x, header_y), 4.0, 4.0)

        painter.setPen(Config.COLOR_TEXT_SECONDARY)
        font_header = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
        painter.setFont(font_header)
        painter.drawText(
            QRectF(dot_x + 12.0, header_y - 8.0, 200.0, 16.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "RÉPONSE D'ANTIGRAVITY"
        )

        # Mini waveform voix
        wave_cx = rect.right() - 40.0
        self.waveform.draw(painter, wave_cx, header_y, max_height=14.0, color=Config.COLOR_ACCENT_CYAN)

        # Message textuel principal
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
        """Contenu de mission / action de fond."""
        top_y = rect.top() + 16.0
        dot_x = rect.left() + 24.0

        # Badge Orange Action
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

        # Titre d'action
        painter.setPen(Config.COLOR_TEXT_PRIMARY)
        font_title = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
        painter.setFont(font_title)
        painter.drawText(
            QRectF(rect.left() + 24.0, top_y + 12.0, rect.width() - 48.0, 22.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.action_title
        )

        # Détail
        painter.setPen(Config.COLOR_TEXT_SECONDARY)
        font_detail = QFont("Segoe UI", 9, QFont.Weight.Normal)
        painter.setFont(font_detail)
        painter.drawText(
            QRectF(rect.left() + 24.0, top_y + 36.0, rect.width() - 48.0, 20.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.action_detail or "Exécution des sous-tâches..."
        )

        # Barre de progression fine
        bar_w = rect.width() - 48.0
        bar_h = 3.5
        bar_x = rect.left() + 24.0
        bar_y = rect.bottom() - 20.0
        
        painter.setBrush(QBrush(QColor(255, 255, 255, 20)))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2.0, 2.0)
        
        # Progression active
        active_w = max(4.0, bar_w * min(1.0, max(0.05, self.progress_value)))
        painter.setBrush(QBrush(Config.COLOR_ACCENT_ORANGE))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, active_w, bar_h), 2.0, 2.0)
