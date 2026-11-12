import sys
import math
from PyQt6.QtCore import (
    Qt, QRect, QRectF, QPointF, QTimer, QVariantAnimation, QEasingCurve, pyqtSignal
)
from PyQt6.QtWidgets import QWidget, QApplication, QMenu, QLineEdit
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QPainterPath, QRadialGradient
)

from island.config import Config
from island.components.waveform import WaveformVisualizer
from island.components.glowing_orb import GlowingOrb
from island.pointer import PointerOverlay
from island.voice import VoiceEngine
from island.window_manager import MinimizedWindowTracker
from island.notifications import WindowsNotificationListener
from island.notification_manager import NotificationManager

def create_iphone_x_notch_path(x: float, y: float, w: float, h: float, r_bottom: float = 14.0, r_ear: float = 8.0) -> QPainterPath:
    """Génère la forme géométrique authentique d'une encoche style iPhone X / MacBook avec cornes concaves."""
    path = QPainterPath()
    # Démarre sur le bord supérieur à gauche de l'encoche
    path.moveTo(x - r_ear, y)
    # Courbe concave (oreille gauche) descendant dans le bord gauche
    path.cubicTo(
        x - r_ear * 0.45, y,
        x, y + r_ear * 0.45,
        x, y + r_ear
    )
    # Ligne verticale gauche
    path.lineTo(x, y + h - r_bottom)
    # Arrondi inférieur gauche
    path.cubicTo(
        x, y + h - r_bottom * 0.45,
        x + r_bottom * 0.45, y + h,
        x + r_bottom, y + h
    )
    # Ligne horizontale inférieure
    path.lineTo(x + w - r_bottom, y + h)
    # Arrondi inférieur droit
    path.cubicTo(
        x + w - r_bottom * 0.45, y + h,
        x + w, y + h - r_bottom * 0.45,
        x + w, y + h - r_bottom
    )
    # Ligne verticale droite
    path.lineTo(x + w, y + r_ear)
    # Courbe concave (oreille droite) remontant vers le bord supérieur
    path.cubicTo(
        x + w, y + r_ear * 0.45,
        x + w + r_ear * 0.45, y,
        x + w + r_ear, y
    )
    path.closeSubpath()
    return path

def draw_vector_microphone(painter: QPainter, cx: float, cy: float, color: QColor, scale: float = 1.0):
    """Dessine une icône de microphone vectorielle épurée style Apple / Siri."""
    painter.save()
    s = scale
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    
    # 1. Corps de la capsule (arrondi)
    capsule_w = 6.0 * s
    capsule_h = 10.0 * s
    capsule_r = 3.0 * s
    capsule_rect = QRectF(cx - capsule_w / 2.0, cy - capsule_h / 2.0 - 1.5 * s, capsule_w, capsule_h)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(color))
    painter.drawRoundedRect(capsule_rect, capsule_r, capsule_r)

    # 2. Berceau sous la capsule
    pen = QPen(color, 1.3 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    cradle_path = QPainterPath()
    cradle_w = 11.0 * s
    cradle_h = 9.0 * s
    cradle_rect = QRectF(cx - cradle_w / 2.0, cy - 3.5 * s, cradle_w, cradle_h)
    cradle_path.arcMoveTo(cradle_rect, 0)
    cradle_path.arcTo(cradle_rect, 0, -180)
    painter.drawPath(cradle_path)

    # 3. Pied et base
    painter.drawLine(QPointF(cx, cy + 5.5 * s), QPointF(cx, cy + 8.5 * s))
    painter.drawLine(QPointF(cx - 3.5 * s, cy + 8.5 * s), QPointF(cx + 3.5 * s, cy + 8.5 * s))
    painter.restore()

def draw_vector_expand_icon(painter: QPainter, cx: float, cy: float, color: QColor, scale: float = 1.0, is_expanded: bool = False):
    """Dessine une icône vectorielle d'expansion (chevron ⌄ / ⤢) ou de repli (⌃ / ✕)."""
    painter.save()
    s = scale
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color, 1.4 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if not is_expanded:
        path = QPainterPath()
        path.moveTo(cx - 4.5 * s, cy - 2.0 * s)
        path.lineTo(cx, cy + 2.5 * s)
        path.lineTo(cx + 4.5 * s, cy - 2.0 * s)
        painter.drawPath(path)
    else:
        path = QPainterPath()
        path.moveTo(cx - 4.5 * s, cy + 2.0 * s)
        path.lineTo(cx, cy - 2.5 * s)
        path.lineTo(cx + 4.5 * s, cy + 2.0 * s)
        painter.drawPath(path)
    painter.restore()

def draw_vector_camera(painter: QPainter, cx: float, cy: float, color: QColor, scale: float = 1.0):
    painter.save()
    s = scale
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color, 1.2 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(cx - 6.5 * s, cy - 4.0 * s, 13.0 * s, 9.0 * s), 2.0 * s, 2.0 * s)
    painter.drawEllipse(QPointF(cx, cy + 0.5 * s), 2.5 * s, 2.5 * s)
    painter.drawLine(QPointF(cx - 3.5 * s, cy - 5.5 * s), QPointF(cx - 1.5 * s, cy - 5.5 * s))
    painter.restore()

def draw_vector_monitor(painter: QPainter, cx: float, cy: float, color: QColor, scale: float = 1.0):
    painter.save()
    s = scale
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color, 1.2 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(cx - 6.5 * s, cy - 5.0 * s, 13.0 * s, 8.5 * s), 1.5 * s, 1.5 * s)
    painter.drawLine(QPointF(cx, cy + 3.5 * s), QPointF(cx, cy + 6.0 * s))
    painter.drawLine(QPointF(cx - 4.0 * s, cy + 6.0 * s), QPointF(cx + 4.0 * s, cy + 6.0 * s))
    painter.restore()

def draw_vector_gear(painter: QPainter, cx: float, cy: float, color: QColor, scale: float = 1.0):
    painter.save()
    s = scale
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color, 1.2 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawLine(QPointF(cx - 6.0 * s, cy - 2.5 * s), QPointF(cx + 6.0 * s, cy - 2.5 * s))
    painter.drawLine(QPointF(cx - 6.0 * s, cy + 2.5 * s), QPointF(cx + 6.0 * s, cy + 2.5 * s))
    painter.setBrush(QBrush(color))
    painter.drawEllipse(QPointF(cx - 2.0 * s, cy - 2.5 * s), 1.8 * s, 1.8 * s)
    painter.drawEllipse(QPointF(cx + 2.0 * s, cy + 2.5 * s), 1.8 * s, 1.8 * s)
    painter.restore()

def draw_vector_trash(painter: QPainter, cx: float, cy: float, color: QColor, scale: float = 1.0):
    painter.save()
    s = scale
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color, 1.2 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawLine(QPointF(cx - 5.5 * s, cy - 4.0 * s), QPointF(cx + 5.5 * s, cy - 4.0 * s))
    painter.drawLine(QPointF(cx - 2.0 * s, cy - 5.5 * s), QPointF(cx + 2.0 * s, cy - 5.5 * s))
    p = QPainterPath()
    p.moveTo(cx - 4.0 * s, cy - 3.5 * s)
    p.lineTo(cx - 3.2 * s, cy + 5.5 * s)
    p.lineTo(cx + 3.2 * s, cy + 5.5 * s)
    p.lineTo(cx + 4.0 * s, cy - 3.5 * s)
    painter.drawPath(p)
    painter.drawLine(QPointF(cx - 1.2 * s, cy - 1.5 * s), QPointF(cx - 1.0 * s, cy + 3.5 * s))
    painter.drawLine(QPointF(cx + 1.2 * s, cy - 1.5 * s), QPointF(cx + 1.0 * s, cy + 3.5 * s))
    painter.restore()

def draw_vector_keyboard(painter: QPainter, cx: float, cy: float, color: QColor, scale: float = 1.0):
    """Dessine une icône de clavier vectorielle épurée style Apple / SF Symbols."""
    painter.save()
    s = scale
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color, 1.2 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    # Cadre extérieur du clavier
    kw = 16.0 * s
    kh = 11.0 * s
    rect = QRectF(cx - kw / 2.0, cy - kh / 2.0, kw, kh)
    painter.drawRoundedRect(rect, 2.2 * s, 2.2 * s)

    # Rangée supérieure (3 points de touches)
    y1 = cy - 2.2 * s
    painter.drawPoint(QPointF(cx - 4.5 * s, y1))
    painter.drawPoint(QPointF(cx, y1))
    painter.drawPoint(QPointF(cx + 4.5 * s, y1))

    # Rangée médiane (3 points de touches décalés)
    y2 = cy + 0.8 * s
    painter.drawPoint(QPointF(cx - 3.2 * s, y2))
    painter.drawPoint(QPointF(cx, y2))
    painter.drawPoint(QPointF(cx + 3.2 * s, y2))

    # Rangée inférieure (barre d'espace)
    y3 = cy + 3.4 * s
    painter.drawLine(QPointF(cx - 4.2 * s, y3), QPointF(cx + 4.2 * s, y3))
    painter.restore()

def draw_vector_send(painter: QPainter, cx: float, cy: float, color: QColor, scale: float = 1.0):
    """Dessine une flèche vectorielle d'envoi vers le haut style bouton Apple / iMessage."""
    painter.save()
    s = scale
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color, 1.4 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    # Flèche orientée vers le haut
    path = QPainterPath()
    path.moveTo(cx, cy + 4.0 * s)
    path.lineTo(cx, cy - 4.0 * s)
    path.moveTo(cx - 3.5 * s, cy - 0.5 * s)
    path.lineTo(cx, cy - 4.0 * s)
    path.lineTo(cx + 3.5 * s, cy - 0.5 * s)
    painter.drawPath(path)
    painter.restore()

def draw_vector_close(painter: QPainter, cx: float, cy: float, color: QColor, scale: float = 1.0):
    """Dessine une croix de fermeture ✕ vectorielle fine."""
    painter.save()
    s = scale
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color, 1.3 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    d = 3.5 * s
    painter.drawLine(QPointF(cx - d, cy - d), QPointF(cx + d, cy + d))
    painter.drawLine(QPointF(cx - d, cy + d), QPointF(cx + d, cy - d))
    painter.restore()

class PromptLineEdit(QLineEdit):
    """Champ de saisie textuel optimisé pour l'esthétique Apple Obsidian Glass d'Antigravity Island."""
    def __init__(self, parent=None, on_escape=None):
        super().__init__(parent)
        self.on_escape = on_escape

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if callable(self.on_escape):
                self.on_escape()
            event.accept()
            return
        super().keyPressEvent(event)

class IslandWindow(QWidget):
    """
    Fenêtre principale de l'encoche dynamique Antigravity.
    Supporte à la fois le style Dynamic Island (pilule) et l'encoche iPhone X (notch avec cornes).
    Collée au plus près du bord supérieur de l'écran Windows, sans bordure et ultra-fluide.
    """
    
    _instance = None
    state_change_requested = pyqtSignal(str, dict)

    @classmethod
    def get_instance(cls):
        return cls._instance

    def __init__(self):
        super().__init__()
        IslandWindow._instance = self
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.current_state = "idle"
        cfg = Config.STATES[self.current_state]
        
        self.custom_idle_w = 176.0
        self.custom_idle_h = 32.0
        
        self.cur_w = float(self.custom_idle_w)
        self.cur_h = float(self.custom_idle_h)
        self.cur_r = float(self.custom_idle_h / 2.0)
        self.target_w = self.cur_w
        self.target_h = self.cur_h
        self.target_r = self.cur_r

        # Boutons d'interaction explicite & vectoriels
        self.btn_manual_ask_rect = QRectF()
        self.btn_keyboard_ask_rect = QRectF()
        self.btn_expand_rect = QRectF()
        self.btn_collapse_rect = QRectF()
        self.btn_prompt_send_rect = QRectF()
        self.btn_prompt_cancel_rect = QRectF()
        self.hovered_action_btn = None
        self.ptt_engine = None

        # Champ de saisie prompt clavier (Obsidian Glass)
        self.prompt_input = PromptLineEdit(self, on_escape=self._on_prompt_escape)
        self.prompt_input.setPlaceholderText("Demandez à Island... (Entrée pour valider)")
        self.prompt_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                color: #f8fafc;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
                padding-left: 6px;
                padding-right: 6px;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
            }
            QLineEdit:focus {
                border: none;
                outline: none;
            }
        """)
        self.prompt_input.returnPressed.connect(self._on_prompt_input_submitted)
        self.prompt_input.hide()

        # Minuteur d'écoute manuelle (max 7.5s avant analyse automatique si pas de re-clic)
        self.manual_listen_timer = QTimer(self)
        self.manual_listen_timer.setSingleShot(True)
        self.manual_listen_timer.timeout.connect(self.stop_manual_ask)

        # Minuteur debounce d'expansion vers le haut (anti-saccade)
        self.hover_expand_timer = QTimer(self)
        self.hover_expand_timer.setSingleShot(True)
        self.hover_expand_timer.timeout.connect(self._on_hover_expand_timeout)

        # Paramètres de disposition et style
        self.style_mode = "island"      # "island" (pilule) ou "iphonex" (encoche iPhone X)
        self.position_mode = "notch"   # "notch" (collé au header à Y=0) ou "floating"
        self.alignment = "center"       # "center", "left", "right"
        self.screen_index = 0           # Index de l'écran cible (Multi-Moniteurs)
        self.top_margin = 0
        self.accent_color = Config.COLOR_ACCENT_CYAN
        self.island_bg_color = "#08080a"

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

        # Composants vocaux et contrôle
        self.settings_window = None
        self.voice_enabled = False  # Désactivé par défaut : affichage textuel direct sur le Dynamic Island
        self.voice_engine = VoiceEngine(window_instance=self)

        # Animation morphique
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(350)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.valueChanged.connect(self._on_anim_step)

        # Timer 60 FPS
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self._on_tick)
        self.render_timer.start(16)

        # Pointeur virtuel & surbrillance d'écran (HeyClicky inspired)
        self.pointer = PointerOverlay()

        self.setMouseTracking(True)

        # Suivi des fenêtres ouvertes et réduites (Dock Dynamic Island)
        self.tracker = MinimizedWindowTracker()
        self.open_windows = []
        self.minimized_windows = []
        self.hovered_dock_index = -1
        self.hovered_hub_btn = None
        self.hovered_hub_app = -1
        self.hovered_hub_notif = -1
        self.btn_screenshot_rect = QRectF()
        self.btn_desktop_rect = QRectF()
        self.btn_settings_rect = QRectF()
        self.btn_clear_notifs_rect = QRectF()
        self.hub_app_rects = []
        self.hub_notif_rects = []
        self.minimized_timer = QTimer(self)
        self.minimized_timer.timeout.connect(self._check_open_windows)
        self.minimized_timer.start(2000)

        # Gestionnaire de notifications & historique carrousel
        self.notif_mgr = NotificationManager(max_items=50)
        self.notif_btn_clear_rect = QRectF()
        self.notif_btn_prev_rect = QRectF()
        self.notif_btn_next_rect = QRectF()

        # Debounce de sortie pour éviter l'oscillation et les crashs de redimensionnement
        self.leave_debounce_timer = QTimer(self)
        self.leave_debounce_timer.setSingleShot(True)
        self.leave_debounce_timer.timeout.connect(self._on_leave_timeout)
        self._hover_top_count = 0

        # Écouteur de notifications Windows Toast (WhatsApp, Discord, etc.)
        self.notif_listener = WindowsNotificationListener(self)
        self.notif_listener.notification_received.connect(self.on_notification_received)
        self.notif_listener.start()

        self.notif_timer = QTimer(self)
        self.notif_timer.setSingleShot(True)
        self.notif_timer.timeout.connect(lambda: self.current_state == "notification" and self.set_state("idle"))

        # Timer pour la lecture de réponse textuelle
        self.reading_timer = QTimer(self)
        self.reading_timer.setSingleShot(True)
        self.reading_timer.timeout.connect(lambda: self.current_state == "speaking" and self.set_state("idle"))

        # Watchdog de sécurité pour l'état thinking (timeout 20s max pour ne jamais rester bloqué)
        self.thinking_watchdog = QTimer(self)
        self.thinking_watchdog.setSingleShot(True)
        self.thinking_watchdog.timeout.connect(lambda: self.current_state == "thinking" and self.set_state("idle"))

        self.state_change_requested.connect(self.apply_remote_command)
        self._update_geometry()

    def apply_settings(self, settings: dict):
        if "accent_color" in settings:
            self.accent_color = QColor(settings["accent_color"])
        if "island_bg_color" in settings:
            self.island_bg_color = settings["island_bg_color"]
        if "style_mode" in settings:
            self.style_mode = settings["style_mode"]
        if "position_mode" in settings:
            self.position_mode = settings["position_mode"]
            self.top_margin = 0 if self.position_mode == "notch" else 12
        if "alignment" in settings:
            self.alignment = settings["alignment"]
        if "screen_index" in settings:
            self.screen_index = int(settings["screen_index"])
        if "idle_width" in settings:
            self.custom_idle_w = float(settings["idle_width"])
        if "idle_height" in settings:
            self.custom_idle_h = float(settings["idle_height"])
        if "voice_enabled" in settings:
            self.voice_enabled = bool(settings["voice_enabled"])
        if "voice_name" in settings and hasattr(self, "voice_engine"):
            self.voice_engine.set_voice(settings["voice_name"])
        if "voice_rate" in settings and hasattr(self, "voice_engine"):
            self.voice_engine.set_rate(settings["voice_rate"])
        if "island_visible" in settings:
            if settings["island_visible"]:
                self.show()
            else:
                self.hide()

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
        if state_name not in Config.STATES:
            return

        # Éviter les saccades si l'état cible est déjà actif et en cours d'animation
        if state_name == self.current_state and self.anim.state() == QVariantAnimation.State.Running:
            return
            
        self.current_state = state_name

        if state_name != "prompt_input":
            if hasattr(self, "prompt_input") and self.prompt_input.isVisible():
                self.prompt_input.hide()
        
        if state_name in ["idle", "listening", "thinking"]:
            self.action_title = ""
            self.action_detail = ""
        if state_name in ["listening", "thinking"]:
            self.reading_timer.stop()
        if state_name == "thinking":
            self.thinking_watchdog.start(20000)
        else:
            self.thinking_watchdog.stop()

        if payload:
            if "text" in payload:
                self.message_text = payload["text"]
            if "title" in payload and state_name not in ["thinking", "listening", "idle"]:
                self.action_title = payload["title"]
            if "detail" in payload and state_name not in ["thinking", "listening", "idle"]:
                self.action_detail = payload["detail"]
            if "progress" in payload:
                self.progress_value = float(payload["progress"])

        self.anim.stop()
        self.start_w = self.cur_w
        self.start_h = self.cur_h
        self.start_r = self.cur_r
        
        if state_name == "idle":
            self.custom_idle_w = max(176.0, float(self.custom_idle_w))
            self.target_w = float(self.custom_idle_w)
            self.target_h = float(self.custom_idle_h)
            self.target_r = float(self.custom_idle_h / 2.0)
        elif state_name == "speaking":
            target_cfg = Config.STATES[state_name]
            # Calcul dynamique de la hauteur selon le texte pour ne jamais rien couper
            font_msg = QFont("Segoe UI", 10, QFont.Weight.Normal)
            from PyQt6.QtGui import QFontMetrics
            fm = QFontMetrics(font_msg)
            avail_w = int(target_cfg.width - 48)
            rect_text = fm.boundingRect(0, 0, avail_w, 2000, int(Qt.TextFlag.TextWordWrap), self.message_text)
            needed_h = 16 + 16 + 8 + rect_text.height() + 18
            self.target_w = float(target_cfg.width)
            self.target_h = max(float(target_cfg.height), min(200.0, float(needed_h)))
            self.target_r = 26.0
        elif state_name == "prompt_input":
            target_cfg = Config.STATES[state_name]
            self.target_w = float(target_cfg.width)
            self.target_h = float(target_cfg.height)
            self.target_r = float(target_cfg.radius)
        elif state_name == "notification":
            self.target_w = 460.0
            self.target_h = 76.0
            self.target_r = 26.0
        elif state_name == "minimized_dock":
            wins_count = min(10, len(self.open_windows))
            self.target_w = max(460.0, 110.0 + wins_count * 44.0 + 190.0)
            self.target_h = 54.0
            self.target_r = 24.0
        elif state_name == "control_hub":
            self.target_w = 700.0
            self.target_h = 280.0
            self.target_r = 28.0
        elif state_name == "thinking":
            target_cfg = Config.STATES[state_name]
            self.target_w = float(target_cfg.width)
            self.target_h = float(target_cfg.height)
            self.target_r = float(target_cfg.radius)
        else:
            target_cfg = Config.STATES[state_name]
            self.target_w = float(target_cfg.width)
            self.target_h = float(target_cfg.height)
            self.target_r = float(target_cfg.radius)
        
        if state_name in ["speaking", "action", "notification", "minimized_dock", "control_hub", "prompt_input"]:
            self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim.setDuration(280)
        else:
            self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            self.anim.setDuration(260)
            
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def _on_hover_expand_timeout(self):
        """Déclenché si le curseur est resté sur la zone haute du dock de manière stable."""
        from PyQt6.QtGui import QCursor
        global_pos = QCursor.pos()
        if self.geometry().contains(global_pos) and self.current_state == "minimized_dock":
            local_pos = self.mapFromGlobal(global_pos)
            if local_pos.y() <= 16.0:
                self.set_state("control_hub")

    def trigger_manual_ask(self):
        """Déclenche la demande manuelle à l'Island (enregistrement vocal ou toggle écoute)."""
        if self.current_state == "listening":
            self.stop_manual_ask()
            return

        print("[Island] Déclenchement manuel de la demande à l'Island.")
        self.reading_timer.stop()
        if getattr(self, "voice_engine", None):
            self.voice_engine.stop()

        if getattr(self, "ptt_engine", None):
            self.ptt_engine.start_manual_recording()
        else:
            self.set_state("listening")

        # Watchdog d'écoute manuelle (7.5s max si l'utilisateur ne clique pas à nouveau)
        self.manual_listen_timer.start(7500)

    def stop_manual_ask(self):
        """Arrête l'enregistrement manuel et passe à l'analyse de la requête."""
        self.manual_listen_timer.stop()
        if getattr(self, "ptt_engine", None):
            self.ptt_engine.stop_manual_recording()
        else:
            self.set_state("thinking")

    def trigger_keyboard_ask(self):
        """Active le mode de saisie textuelle pour poser une question au clavier à Island."""
        print("[Island] Déclenchement de la saisie textuelle au clavier.")
        self.reading_timer.stop()
        if getattr(self, "voice_engine", None):
            self.voice_engine.stop()
        self.set_state("prompt_input")
        self.activateWindow()
        self.raise_()
        self.prompt_input.clear()
        self.prompt_input.show()
        self.prompt_input.setFocus()

    def _on_prompt_escape(self):
        """Annule la saisie clavier et replie l'Island en mode repos (idle)."""
        if hasattr(self, "prompt_input"):
            self.prompt_input.clear()
            self.prompt_input.hide()
        self.set_state("idle")

    def _on_prompt_input_submitted(self):
        """Valide et transmet la question saisie au clavier à Antigravity Island."""
        if not hasattr(self, "prompt_input"):
            return
        query = self.prompt_input.text().strip()
        if not query:
            self._on_prompt_escape()
            return

        print(f"[Island] Question clavier reçue : '{query}'")
        self.prompt_input.clear()
        self.prompt_input.hide()
        self.submit_text_query(query)

    def submit_text_query(self, query: str):
        """Exécute la requête textuelle en arrière-plan avec streaming et mémoire conversationnelle DeepTalk."""
        self.reading_timer.stop()
        if getattr(self, "voice_engine", None):
            self.voice_engine.stop()

        self.set_state("thinking")

        import threading
        import re
        import time
        import json
        import os
        from island.brain import generate_response

        def worker():
            accumulated_chunks = []
            def on_stream_chunk(chunk: str):
                accumulated_chunks.append(chunk)
                streamed = "".join(accumulated_chunks).strip()
                streamed = re.sub(r'[*_`]', '', streamed)
                if streamed:
                    self.state_change_requested.emit("stream_text", {"text": streamed})

            try:
                response_text = generate_response(query, on_chunk=on_stream_chunk)
                if not response_text or not response_text.strip():
                    response_text = "Je n'ai pas pu obtenir de réponse. Réessayez."
                    is_status = True
                else:
                    is_status = False
            except Exception as e:
                print(f"[Island] Exception dans generate_response (clavier) : {e}")
                response_text = "Une erreur est survenue lors de l'analyse."
                is_status = True

            # Sauvegarde pour traçabilité et historique
            try:
                appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
                storage_dir = os.path.join(appdata, "AntigravityIsland")
                os.makedirs(storage_dir, exist_ok=True)
                query_path = os.path.join(storage_dir, "last_keyboard_query.json")
                payload = {
                    "timestamp": time.time(),
                    "query": query,
                    "response": response_text,
                    "has_audio": False,
                    "input_type": "keyboard"
                }
                with open(query_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

            self.state_change_requested.emit("speak", {
                "text": response_text,
                "is_status": is_status,
                "is_answer": not is_status
            })

        threading.Thread(target=worker, daemon=True).start()

    def _on_anim_step(self, progress: float):
        self.cur_w = self.start_w + (self.target_w - self.start_w) * progress
        self.cur_h = self.start_h + (self.target_h - self.start_h) * progress
        self.cur_r = self.start_r + (self.target_r - self.start_r) * progress
        self._update_geometry()
        self.update()

    def _update_geometry(self):
        screens = QApplication.screens()
        if screens and 0 <= self.screen_index < len(screens):
            screen = screens[self.screen_index]
        else:
            screen = QApplication.primaryScreen()
        if not screen:
            return
        screen_geo = screen.geometry()
        
        pad_x = Config.SHADOW_BLUR + 16  # Marge pour les oreilles de l'iPhone X
        pad_top = 0 if self.position_mode == "notch" else Config.SHADOW_BLUR
        
        total_w = int(self.cur_w + pad_x * 2)
        total_h = int(self.cur_h + pad_top + Config.SHADOW_BLUR + Config.SHADOW_OFFSET_Y)
        
        if self.alignment == "left":
            x = screen_geo.x() + 40
        elif self.alignment == "right":
            x = screen_geo.x() + screen_geo.width() - total_w - 40
        else:
            x = screen_geo.x() + (screen_geo.width() - total_w) // 2

        if self.position_mode == "notch":
            y = screen_geo.y()
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
        elif action == "stop_reading":
            self.reading_timer.stop()
        elif action == "stream_text":
            self.reading_timer.stop()
            self.message_text = data.get("text", "")
            if self.current_state != "speaking":
                self.set_state("speaking", data)
            self.update()
        elif action == "speak":
            self.reading_timer.stop()
            self.message_text = data.get("text", "")
            self.set_state("speaking", data)
            if getattr(self, "voice_enabled", False):
                import time
                def on_done():
                    time.sleep(1.2)
                    self.state_change_requested.emit("idle", {})
                self.voice_engine.speak(self.message_text, callback_on_finish=on_done)
            else:
                # Règle UX demandée par l'utilisateur :
                # 1. Affirmations/statuts courts de l'Island -> 2 secondes (2000 ms)
                # 2. Réponses explicatives ou réponses aux questions -> NE disparaissent PAS tant que l'utilisateur ne clique pas sur l'orbe ou l'Island !
                txt_lower = self.message_text.lower().strip()
                is_status = data.get("is_status", False) or any(kw in txt_lower for kw in [
                    "inaudible", "pas bien compris", "suis prêt", "suis pret", "à votre écoute",
                    "a votre ecoute", "analys", "réessayez", "reessayez", "parlez un peu plus",
                    "prêt !", "pret !", "saut de ligne", "texte saisi", "verrouillée", "bureau affiché"
                ]) and not data.get("is_answer", False)

                if is_status:
                    self.reading_timer.start(2000)
                else:
                    # Reste ouvert indéfiniment jusqu'au clic utilisateur
                    self.reading_timer.stop()
        elif action in ["trigger_keyboard_ask", "prompt_input", "ask_keyboard"]:
            self.trigger_keyboard_ask()
        elif action == "submit_text_query":
            text = data.get("text", "")
            if text:
                self.submit_text_query(text)
        elif action == "audio_power":
            self.audio_power = float(data.get("power", 0.0))
        elif action == "action":
            self.set_state("action", data)
        elif action == "idle":
            self.set_state("idle", data)
        elif action in ["set_style", "style"]:
            style = data.get("style", "island")
            self.apply_settings({"style_mode": style})
        elif action == "settings":
            self.apply_settings(data.get("settings", {}))
        elif action in ["show_control_center", "show_settings"]:
            if getattr(self, "settings_window", None):
                self.settings_window.show()
                self.settings_window.raise_()
                self.settings_window.activateWindow()
        elif action == "point_at":
            x = data.get("x", 500)
            y = data.get("y", 300)
            label = data.get("label", "")
            duration = float(data.get("duration", 3.5))
            color = data.get("color", None)
            self.pointer.point_at(x, y, label, duration, color)

    def on_notification_received(self, app_name: str, title: str, message: str, color_hex: str):
        if self.current_state in ["listening", "thinking"]:
            return
        self.notif_mgr.add(app_name, title, message, color_hex)
        self.set_state("notification")
        self.notif_timer.start(6500)

    def wheelEvent(self, event):
        super().wheelEvent(event)
        if self.current_state == "notification" and self.notif_mgr.count() > 1:
            delta = event.angleDelta().y()
            if delta < 0:
                self.notif_mgr.next()
            else:
                self.notif_mgr.prev()
            self.notif_timer.start(7500)  # Réinitialise la durée d'affichage au scroll
            self.update()

    def _check_open_windows(self):
        try:
            # Ne pas solliciter EnumWindows trop agressivement en mode idle
            wins = self.tracker.get_all_open_windows()
            prev_count = len(self.open_windows)
            self.open_windows = list(wins)
            self.minimized_windows = [w for w in self.open_windows if w.get("is_minimized")]
            if len(self.open_windows) != prev_count:
                if self.current_state == "minimized_dock":
                    if len(self.open_windows) == 0:
                        self.set_state("idle")
                    else:
                        new_w = max(280.0, 70.0 + min(10, len(self.open_windows)) * 44.0)
                        self.target_w = new_w
                        self.anim.stop()
                        self.cur_w = new_w
                        self._update_geometry()
                self.update()
        except Exception as e:
            print("[_check_open_windows] Error:", e)

    _check_minimized_windows = _check_open_windows

    def take_quick_screenshot(self):
        """Capture d'écran instantanée, copie dans le presse-papier et affichage dynamique."""
        try:
            from island.vision import capture_screen
            res = capture_screen()
            file_path = res.get("file_path", "")
            if file_path:
                from PyQt6.QtGui import QImage
                img = QImage(file_path)
                if not img.isNull():
                    QApplication.clipboard().setImage(img)
            self.notif_mgr.add("Capture d'écran", "Capture plein écran", "Image copiée dans le presse-papier", "#22c55e")
            self.set_state("notification")
            self.notif_timer.start(3500)
        except Exception as e:
            print("[Screenshot] Erreur :", e)

    def _on_leave_timeout(self):
        from PyQt6.QtGui import QCursor
        global_pos = QCursor.pos()
        # En mode notch, si la souris est tout en haut de l'écran (Y <= 3), l'utilisateur survole l'encoche
        if self.position_mode == "notch" and global_pos.y() <= 3:
            geo = self.geometry()
            if geo.x() <= global_pos.x() <= geo.x() + geo.width():
                return
        if not self.geometry().contains(global_pos):
            if self.current_state in ["minimized_dock", "control_hub"]:
                self.set_state("idle")

    def enterEvent(self, event):
        super().enterEvent(event)
        self.leave_debounce_timer.stop()
        self._check_open_windows()
        if self.current_state == "idle":
            self.set_state("minimized_dock")

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.hovered_dock_index = -1
        self.hovered_action_btn = None
        self.hovered_hub_app = -1
        self.hovered_hub_notif = -1
        self.hover_expand_timer.stop()
        if self.current_state in ["minimized_dock", "control_hub"]:
            self.leave_debounce_timer.start(350)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        pos = event.position()
        self.leave_debounce_timer.stop()

        # Détection du survol des boutons d'actions tactiles
        prev_action_btn = self.hovered_action_btn
        if self.btn_manual_ask_rect.contains(pos):
            self.hovered_action_btn = "ask"
        elif self.btn_keyboard_ask_rect.contains(pos):
            self.hovered_action_btn = "keyboard_ask"
        elif self.btn_expand_rect.contains(pos):
            self.hovered_action_btn = "expand"
        elif self.btn_collapse_rect.contains(pos):
            self.hovered_action_btn = "collapse"
        elif self.current_state == "prompt_input":
            if self.btn_prompt_send_rect.contains(pos):
                self.hovered_action_btn = "prompt_send"
            elif self.btn_prompt_cancel_rect.contains(pos):
                self.hovered_action_btn = "prompt_cancel"
            else:
                self.hovered_action_btn = None
        elif self.current_state == "control_hub":
            if self.btn_screenshot_rect.contains(pos):
                self.hovered_action_btn = "screenshot"
            elif self.btn_desktop_rect.contains(pos):
                self.hovered_action_btn = "desktop"
            elif self.btn_settings_rect.contains(pos):
                self.hovered_action_btn = "settings"
            elif self.btn_clear_notifs_rect.contains(pos):
                self.hovered_action_btn = "clear_notifs"
            else:
                self.hovered_action_btn = None
        else:
            self.hovered_action_btn = None

        if self.hovered_action_btn != prev_action_btn:
            self.update()

        if self.current_state == "minimized_dock":
            # Expansion fluide et sans saccade vers le Super Hub si le curseur remonte de façon stable
            if pos.y() <= 14.0:
                if not self.hover_expand_timer.isActive():
                    self.hover_expand_timer.start(160)
            else:
                self.hover_expand_timer.stop()

            pad_x = Config.SHADOW_BLUR + 16.0
            dock_x = pad_x + 76.0  # Marge pour les boutons micro et clavier à gauche
            cy = self.height() / 2.0
            hovered = -1
            display_wins = self.open_windows[:10]
            for i in range(len(display_wins)):
                tile_rect = QRectF(dock_x + i * 44.0, cy - 18.0, 36.0, 36.0)
                if tile_rect.contains(pos):
                    hovered = i
                    break
            if hovered != self.hovered_dock_index:
                self.hovered_dock_index = hovered
                self.update()

        elif self.current_state == "control_hub":
            self.hover_expand_timer.stop()

            # Survol des cartes d'applications
            hovered_app = -1
            for i, r in enumerate(self.hub_app_rects):
                if r.contains(pos):
                    hovered_app = i
                    break
            if hovered_app != self.hovered_hub_app:
                self.hovered_hub_app = hovered_app
                self.update()

            # Survol des notifications
            hovered_notif = -1
            for i, r in enumerate(self.hub_notif_rects):
                if r.contains(pos):
                    hovered_notif = i
                    break
            if hovered_notif != self.hovered_hub_notif:
                self.hovered_hub_notif = hovered_notif
                self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.current_state == "prompt_input":
                self._on_prompt_escape()
                event.accept()
                return
            elif self.current_state in ["control_hub", "minimized_dock", "speaking", "notification"]:
                self.set_state("idle")
                event.accept()
                return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()

            # 1. Clic sur le bouton de demande manuelle à l'Island (Ask / Mic)
            if self.btn_manual_ask_rect.contains(pos):
                self.trigger_manual_ask()
                return

            # 2. Clic sur le bouton de saisie au clavier (Keyboard Ask)
            if self.btn_keyboard_ask_rect.contains(pos):
                self.trigger_keyboard_ask()
                return

            # 3. Clic sur le bouton d'expansion latérale (Super Hub)
            if self.btn_expand_rect.contains(pos):
                self.set_state("control_hub")
                return

            # 4. Clic sur le bouton de repli / fermeture
            if self.btn_collapse_rect.contains(pos):
                self.set_state("idle")
                return

            # 5. En état prompt_input : validation ou annulation
            if self.current_state == "prompt_input":
                if self.btn_prompt_send_rect.contains(pos):
                    self._on_prompt_input_submitted()
                    return
                elif self.btn_prompt_cancel_rect.contains(pos):
                    self._on_prompt_escape()
                    return
                return

            # 6. En état d'écoute vocale : un clic n'importe où sur l'Island valide et lance l'analyse
            if self.current_state == "listening":
                self.stop_manual_ask()
                return

            if self.current_state == "minimized_dock":
                display_wins = self.open_windows[:10]
                if 0 <= self.hovered_dock_index < len(display_wins):
                    win = display_wins[self.hovered_dock_index]
                    self.tracker.activate_window(win["hwnd"])
                    self._check_open_windows()
                    self.set_state("idle")
                    return

            elif self.current_state == "control_hub":
                # Actions rapides
                if self.btn_screenshot_rect.contains(pos):
                    self.take_quick_screenshot()
                    return
                elif self.btn_desktop_rect.contains(pos):
                    from island.automation import press_key
                    press_key("win+d")
                    self.set_state("idle")
                    return
                elif self.btn_settings_rect.contains(pos):
                    if getattr(self, "settings_window", None):
                        self.settings_window.show()
                        self.settings_window.raise_()
                        self.settings_window.activateWindow()
                    self.set_state("idle")
                    return
                elif self.btn_clear_notifs_rect.contains(pos):
                    self.notif_mgr.clear_all()
                    self.update()
                    return

                # Clic sur une carte d'application dans la grille
                if 0 <= self.hovered_hub_app < len(self.open_windows):
                    win = self.open_windows[self.hovered_hub_app]
                    self.tracker.activate_window(win["hwnd"])
                    self._check_open_windows()
                    self.set_state("idle")
                    return

                # Clic sur une notification dans le flux
                if 0 <= self.hovered_hub_notif < len(self.notif_mgr.items):
                    self.notif_mgr.current_index = self.hovered_hub_notif
                    self.set_state("notification")
                    self.notif_timer.start(5000)
                    return

                self.set_state("idle")
                return

            elif self.current_state == "notification":
                if self.notif_btn_clear_rect.contains(pos):
                    self.notif_mgr.clear_all()
                    self.notif_timer.stop()
                    self.set_state("idle")
                    return
                elif self.notif_btn_prev_rect.contains(pos):
                    self.notif_mgr.prev()
                    self.notif_timer.start(7500)
                    self.update()
                    return
                elif self.notif_btn_next_rect.contains(pos):
                    self.notif_mgr.next()
                    self.notif_timer.start(7500)
                    self.update()
                    return
                else:
                    self.notif_timer.stop()
                    self.set_state("idle")
                    return

            elif self.current_state != "idle":
                self.set_state("idle")
                return

            # En mode idle : clic ouvre / met en avant le Centre de contrôle
            if getattr(self, "settings_window", None):
                if self.settings_window.isVisible():
                    self.settings_window.hide()
                else:
                    self.settings_window.show()
                    self.settings_window.raise_()
                    self.settings_window.activateWindow()
        elif event.button() == Qt.MouseButton.RightButton:
            # Menu contextuel au clic droit
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #0b1120;
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 8px;
                    padding: 4px;
                    font-family: 'Segoe UI';
                    font-size: 12px;
                }
                QMenu::item {
                    padding: 6px 18px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: #38bdf8;
                    color: #000000;
                    font-weight: bold;
                }
            """)
            act_settings = menu.addAction("Centre de contrôle...")
            act_settings.triggered.connect(lambda: getattr(self, "settings_window", None) and (self.settings_window.show(), self.settings_window.raise_(), self.settings_window.activateWindow()))
            act_idle = menu.addAction("Remettre au repos (Idle)")
            act_idle.triggered.connect(lambda: self.set_state("idle"))
            menu.addSeparator()
            act_quit = menu.addAction("Quitter Antigravity Island")
            act_quit.triggered.connect(QApplication.instance().quit)
            menu.exec(event.globalPosition().toPoint())

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

            pad_x = Config.SHADOW_BLUR + 16.0
            pad_top = 0.0 if self.position_mode == "notch" else float(Config.SHADOW_BLUR)
            
            pill_rect = QRectF(pad_x, pad_top, self.cur_w, self.cur_h)
            radius = min(self.cur_r, self.cur_h / 2.0)

            # 1. Ombre portée douce
            shadow_path = QPainterPath()
            if self.style_mode == "iphonex" and self.position_mode == "notch":
                shadow_path = create_iphone_x_notch_path(
                    pad_x - 1, pad_top, self.cur_w + 2, self.cur_h + 4, r_bottom=radius + 2, r_ear=10.0
                )
            elif self.position_mode == "notch":
                shadow_rect = pill_rect.adjusted(-2, 0, 2, 8)
                shadow_path.addRoundedRect(shadow_rect, radius, radius)
            else:
                shadow_rect = pill_rect.adjusted(-2, 2, 2, 6)
                shadow_path.addRoundedRect(shadow_rect, radius + 2, radius + 2)
            
            shadow_color = QColor(Config.COLOR_SHADOW)
            painter.fillPath(shadow_path, QBrush(shadow_color))

            # 2. Corps de l'encoche
            if self.style_mode == "iphonex" and self.position_mode == "notch":
                main_path = create_iphone_x_notch_path(
                    pad_x, pad_top, self.cur_w, self.cur_h, r_bottom=radius, r_ear=9.0
                )
            else:
                main_path = QPainterPath()
                main_path.addRoundedRect(pill_rect, radius, radius)

            bg_grad = QLinearGradient(pill_rect.topLeft(), pill_rect.bottomLeft())
            base_col = QColor(getattr(self, "island_bg_color", "#08080a"))
            r, g, b = base_col.red(), base_col.green(), base_col.blue()
            bg_grad.setColorAt(0.0, QColor(min(255, r + 6), min(255, g + 6), min(255, b + 8), 252))
            bg_grad.setColorAt(1.0, QColor(r, g, b, 255))
            painter.fillPath(main_path, QBrush(bg_grad))

            # 3. Finition bordeless pure : Zéro contour gris ou bande grise parasite
            painter.setPen(Qt.PenStyle.NoPen)

            # 4. Détail matériel spécifique iPhone X : Grille haut-parleur
            if self.style_mode == "iphonex":
                speaker_w = min(46.0, self.cur_w * 0.35)
                speaker_h = 3.0
                speaker_x = pill_rect.center().x() - speaker_w / 2.0
                speaker_y = pill_rect.top() + 4.0
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(40, 40, 48, 220)))
                painter.drawRoundedRect(QRectF(speaker_x, speaker_y, speaker_w, speaker_h), 1.5, 1.5)

            # 5. Rendu des contenus selon l'état
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
            elif self.current_state == "notification":
                self._draw_notification_content(painter, pill_rect)
            elif self.current_state == "minimized_dock":
                self._draw_minimized_dock_content(painter, pill_rect)
            elif self.current_state == "control_hub":
                self._draw_control_hub_content(painter, pill_rect)
            elif self.current_state == "prompt_input":
                self._draw_prompt_input_content(painter, pill_rect)
        finally:
            painter.end()

    def _draw_idle_content(self, painter: QPainter, rect: QRectF):
        """Contenu compact au repos — Micro & Clavier à gauche, aura centrale, bouton d'expansion latérale à droite."""
        cy = rect.center().y()
        cx = rect.center().x()
        if self.style_mode == "iphonex":
            cy += 2.0

        acc = getattr(self, "accent_color", Config.COLOR_ACCENT_CYAN)

        # 1. Bouton tactile Demander / Microphone à GAUCHE
        btn_mic_w = 26.0
        btn_mic_h = 24.0
        btn_mic_x = rect.left() + 6.0
        btn_mic_y = cy - btn_mic_h / 2.0
        self.btn_manual_ask_rect = QRectF(btn_mic_x, btn_mic_y, btn_mic_w, btn_mic_h)

        is_h_ask = (self.hovered_action_btn == "ask")
        if is_h_ask:
            painter.setPen(QPen(QColor(acc.red(), acc.green(), acc.blue(), 160), 1.0))
            painter.setBrush(QBrush(QColor(acc.red(), acc.green(), acc.blue(), 45)))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 25), 0.8))
            painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
        painter.drawRoundedRect(self.btn_manual_ask_rect, 12.0, 12.0)
        mic_col = acc if is_h_ask else QColor(255, 255, 255, 200)
        draw_vector_microphone(painter, self.btn_manual_ask_rect.center().x(), cy, mic_col, scale=0.85)

        # 2. Bouton tactile Écrire / Clavier juste à côté du micro
        btn_kb_w = 26.0
        btn_kb_h = 24.0
        btn_kb_x = btn_mic_x + btn_mic_w + 4.0
        btn_kb_y = cy - btn_kb_h / 2.0
        self.btn_keyboard_ask_rect = QRectF(btn_kb_x, btn_kb_y, btn_kb_w, btn_kb_h)

        is_h_kb = (self.hovered_action_btn == "keyboard_ask")
        if is_h_kb:
            painter.setPen(QPen(QColor(acc.red(), acc.green(), acc.blue(), 160), 1.0))
            painter.setBrush(QBrush(QColor(acc.red(), acc.green(), acc.blue(), 45)))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 25), 0.8))
            painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
        painter.drawRoundedRect(self.btn_keyboard_ask_rect, 12.0, 12.0)
        kb_col = acc if is_h_kb else QColor(255, 255, 255, 200)
        draw_vector_keyboard(painter, self.btn_keyboard_ask_rect.center().x(), cy, kb_col, scale=0.85)

        # 3. Bouton tactile d'EXPANSION vers le Super Hub à DROITE
        btn_exp_w = 26.0
        btn_exp_h = 24.0
        btn_exp_x = rect.right() - btn_exp_w - 6.0
        btn_exp_y = cy - btn_exp_h / 2.0
        self.btn_expand_rect = QRectF(btn_exp_x, btn_exp_y, btn_exp_w, btn_exp_h)

        is_h_exp = (self.hovered_action_btn == "expand")
        if is_h_exp:
            painter.setPen(QPen(QColor(255, 255, 255, 120), 1.0))
            painter.setBrush(QBrush(QColor(255, 255, 255, 38)))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 25), 0.8))
            painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
        painter.drawRoundedRect(self.btn_expand_rect, 12.0, 12.0)
        exp_col = QColor(255, 255, 255, 240) if is_h_exp else QColor(255, 255, 255, 160)
        draw_vector_expand_icon(painter, self.btn_expand_rect.center().x(), cy, exp_col, scale=0.9, is_expanded=False)

        # 4. Aura centrale d'Antigravity Island
        dot_pos = QPointF(cx, cy)
        glow = QRadialGradient(dot_pos, 8.5)
        c_glow = QColor(acc)
        c_glow.setAlpha(180)
        glow.setColorAt(0.0, c_glow)
        c_glow_zero = QColor(acc)
        c_glow_zero.setAlpha(0)
        glow.setColorAt(1.0, c_glow_zero)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(dot_pos, 8.5, 8.5)

        painter.setBrush(QBrush(acc))
        painter.drawEllipse(dot_pos, 3.2, 3.2)

        # 4. Indicateur discret d'applications ouvertes
        if len(self.open_windows) > 0:
            count = len(self.open_windows)
            badge_x = btn_exp_x - 22.0
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 22)))
            painter.drawRoundedRect(QRectF(badge_x, cy - 7.0, 18.0, 14.0), 7.0, 7.0)
            painter.setPen(QColor(255, 255, 255, 170))
            font_cnt = QFont("Segoe UI", 7, QFont.Weight.Bold)
            painter.setFont(font_cnt)
            painter.drawText(QRectF(badge_x, cy - 7.0, 18.0, 14.0), Qt.AlignmentFlag.AlignCenter, str(count))

    def _draw_listening_content(self, painter: QPainter, rect: QRectF):
        cy = rect.center().y()
        btn_mic_w = 30.0
        btn_mic_h = 28.0
        btn_mic_x = rect.left() + 14.0
        btn_mic_y = cy - btn_mic_h / 2.0
        self.btn_manual_ask_rect = QRectF(btn_mic_x, btn_mic_y, btn_mic_w, btn_mic_h)

        # Micro vert tactile
        painter.setPen(QPen(QColor(34, 197, 94, 180), 1.0))
        painter.setBrush(QBrush(QColor(34, 197, 94, 40)))
        painter.drawRoundedRect(self.btn_manual_ask_rect, 10.0, 10.0)
        draw_vector_microphone(painter, self.btn_manual_ask_rect.center().x(), cy, Config.COLOR_ACCENT_GREEN, scale=0.9)

        painter.setPen(Config.COLOR_TEXT_PRIMARY)
        font = QFont("Segoe UI", 9, QFont.Weight.Medium)
        painter.setFont(font)
        text_rect = QRectF(btn_mic_x + btn_mic_w + 10.0, rect.top(), 180.0, rect.height())
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

        if getattr(self, "voice_enabled", False):
            wave_cx = rect.right() - 40.0
            self.waveform.draw(painter, wave_cx, header_y, max_height=14.0, color=acc)
        else:
            painter.setPen(QColor(255, 255, 255, 120))
            font_sub = QFont("Segoe UI", 8, QFont.Weight.Medium)
            painter.setFont(font_sub)
            painter.drawText(
                QRectF(rect.right() - 110.0, header_y - 8.0, 90.0, 16.0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                "✕ Fermer"
            )

        painter.setPen(Config.COLOR_TEXT_PRIMARY)
        font_msg = QFont("Segoe UI", 10, QFont.Weight.Normal)
        painter.setFont(font_msg)
        
        msg_rect = QRectF(rect.left() + 24.0, header_y + 12.0, rect.width() - 48.0, rect.height() - header_y - 12.0)
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

    def _draw_notification_content(self, painter: QPainter, rect: QRectF):
        item = self.notif_mgr.get_current()
        if not item:
            self.set_state("idle")
            return

        pad_left = rect.left() + 20.0
        cy = rect.center().y()

        # 1. Logo authentique haute résolution de l'application (WhatsApp, Discord, etc.)
        if item.logo and not item.logo.isNull():
            painter.drawPixmap(int(pad_left), int(cy - 17.0), item.logo)
        else:
            badge_rect = QRectF(pad_left, cy - 17.0, 34.0, 34.0)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(item.color_hex)))
            painter.drawRoundedRect(badge_rect, 10.0, 10.0)
            painter.setPen(QColor(255, 255, 255))
            font_init = QFont("Segoe UI", 12, QFont.Weight.Bold)
            painter.setFont(font_init)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, item.app_name[:1].upper())

        # 2. Bouton « Effacer tout » en haut à droite
        clear_w = 78.0
        clear_h = 20.0
        clear_x = rect.right() - clear_w - 14.0
        clear_y = rect.top() + 12.0
        self.notif_btn_clear_rect = QRectF(clear_x, clear_y, clear_w, clear_h)
        painter.setPen(QPen(QColor(255, 255, 255, 45), 1.0))
        painter.setBrush(QBrush(QColor(255, 255, 255, 18)))
        painter.drawRoundedRect(self.notif_btn_clear_rect, 10.0, 10.0)
        painter.setPen(QColor(255, 255, 255, 200))
        font_btn = QFont("Segoe UI", 7, QFont.Weight.Medium)
        painter.setFont(font_btn)
        painter.drawText(self.notif_btn_clear_rect, Qt.AlignmentFlag.AlignCenter, "Effacer tout")

        # 3. Carrousel scrollable & flèches si plusieurs notifications
        total_count = self.notif_mgr.count()
        content_right_limit = clear_x - 8.0

        if total_count > 1:
            count_w = 34.0
            count_x = clear_x - count_w - 6.0
            count_rect = QRectF(count_x, clear_y, count_w, clear_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 16)))
            painter.drawRoundedRect(count_rect, 10.0, 10.0)
            painter.setPen(QColor(255, 255, 255, 180))
            painter.drawText(count_rect, Qt.AlignmentFlag.AlignCenter, f"{self.notif_mgr.current_index + 1}/{total_count}")

            arr_w = 18.0
            self.notif_btn_prev_rect = QRectF(count_x - arr_w * 2 - 4.0, clear_y, arr_w, clear_h)
            self.notif_btn_next_rect = QRectF(count_x - arr_w - 2.0, clear_y, arr_w, clear_h)

            painter.setPen(QColor(255, 255, 255, 190))
            font_arr = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font_arr)
            painter.drawText(self.notif_btn_prev_rect, Qt.AlignmentFlag.AlignCenter, "‹")
            painter.drawText(self.notif_btn_next_rect, Qt.AlignmentFlag.AlignCenter, "›")
            content_right_limit = self.notif_btn_prev_rect.left() - 8.0
        else:
            self.notif_btn_prev_rect = QRectF()
            self.notif_btn_next_rect = QRectF()

        # 4. Textes de la notification active
        content_x = pad_left + 46.0
        avail_w = max(50.0, content_right_limit - content_x)

        # Ligne 1 : APP NAME • TEMPS
        painter.setPen(QColor(item.color_hex))
        font_app = QFont("Segoe UI", 7, QFont.Weight.Bold)
        painter.setFont(font_app)
        painter.drawText(
            QRectF(content_x, rect.top() + 14.0, avail_w, 14.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            f"{item.app_name.upper()}  •  {item.time_str}"
        )

        # Ligne 2 : Titre (Expéditeur / Contact)
        painter.setPen(Config.COLOR_TEXT_PRIMARY)
        font_title = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font_title)
        title_text = item.title if item.title else item.app_name
        painter.drawText(
            QRectF(content_x, rect.top() + 30.0, rect.width() - content_x - 18.0, 18.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            title_text
        )

        # Ligne 3 : Message
        painter.setPen(Config.COLOR_TEXT_SECONDARY)
        font_msg = QFont("Segoe UI", 8, QFont.Weight.Normal)
        painter.setFont(font_msg)
        msg_text = item.message
        if len(msg_text) > 75:
            msg_text = msg_text[:72] + "..."
        painter.drawText(
            QRectF(content_x, rect.top() + 49.0, rect.width() - content_x - 18.0, 18.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            msg_text
        )

    def _draw_minimized_dock_content(self, painter: QPainter, rect: QRectF):
        pad_left = rect.left() + 12.0
        cy = rect.center().y()
        acc = getattr(self, "accent_color", Config.COLOR_ACCENT_CYAN)

        # 1. Bouton tactile Demander / Microphone à GAUCHE du dock
        btn_mic_w = 30.0
        btn_mic_h = 30.0
        btn_mic_x = pad_left
        btn_mic_y = cy - btn_mic_h / 2.0
        self.btn_manual_ask_rect = QRectF(btn_mic_x, btn_mic_y, btn_mic_w, btn_mic_h)

        is_h_ask = (self.hovered_action_btn == "ask")
        if is_h_ask:
            painter.setPen(QPen(QColor(acc.red(), acc.green(), acc.blue(), 180), 1.0))
            painter.setBrush(QBrush(QColor(acc.red(), acc.green(), acc.blue(), 45)))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 28), 1.0))
            painter.setBrush(QBrush(QColor(255, 255, 255, 14)))
        painter.drawRoundedRect(self.btn_manual_ask_rect, 10.0, 10.0)
        mic_col = acc if is_h_ask else QColor(255, 255, 255, 210)
        draw_vector_microphone(painter, self.btn_manual_ask_rect.center().x(), cy, mic_col, scale=0.9)

        # 2. Bouton tactile Écrire / Clavier juste à côté
        btn_kb_w = 30.0
        btn_kb_h = 30.0
        btn_kb_x = btn_mic_x + btn_mic_w + 6.0
        btn_kb_y = cy - btn_kb_h / 2.0
        self.btn_keyboard_ask_rect = QRectF(btn_kb_x, btn_kb_y, btn_kb_w, btn_kb_h)

        is_h_kb = (self.hovered_action_btn == "keyboard_ask")
        if is_h_kb:
            painter.setPen(QPen(QColor(acc.red(), acc.green(), acc.blue(), 180), 1.0))
            painter.setBrush(QBrush(QColor(acc.red(), acc.green(), acc.blue(), 45)))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 28), 1.0))
            painter.setBrush(QBrush(QColor(255, 255, 255, 14)))
        painter.drawRoundedRect(self.btn_keyboard_ask_rect, 10.0, 10.0)
        kb_col = acc if is_h_kb else QColor(255, 255, 255, 210)
        draw_vector_keyboard(painter, self.btn_keyboard_ask_rect.center().x(), cy, kb_col, scale=0.9)

        # 3. Bouton tactile d'EXPANSION vers le Super Hub à DROITE du dock
        hub_w = 66.0
        hub_h = 28.0
        hub_rect = QRectF(rect.right() - hub_w - 12.0, cy - hub_h / 2.0, hub_w, hub_h)
        self.btn_expand_rect = hub_rect
        is_h_exp = (self.hovered_action_btn == "expand")
        if is_h_exp:
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1.0))
            painter.setBrush(QBrush(QColor(255, 255, 255, 35)))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
            painter.setBrush(QBrush(QColor(255, 255, 255, 16)))
        painter.drawRoundedRect(hub_rect, 9.0, 9.0)
        draw_vector_expand_icon(painter, hub_rect.left() + 15.0, cy, QColor(255, 255, 255, 240 if is_h_exp else 180), scale=0.85, is_expanded=False)
        painter.setPen(QColor(255, 255, 255, 230 if is_h_exp else 190))
        font_hub = QFont("Segoe UI", 7, QFont.Weight.Bold)
        painter.setFont(font_hub)
        painter.drawText(QRectF(hub_rect.left() + 23.0, cy - 10.0, hub_w - 24.0, 20.0), Qt.AlignmentFlag.AlignCenter, "Hub")

        # 4. Icônes d'applications
        dock_start_x = btn_kb_x + btn_kb_w + 12.0
        hovered_win = None
        display_wins = self.open_windows[:10]
        for i, win in enumerate(display_wins):
            tile_x = dock_start_x + i * 44.0
            tile_rect = QRectF(tile_x, cy - 18.0, 36.0, 36.0)

            is_hovered = (i == self.hovered_dock_index)
            if is_hovered:
                hovered_win = win
                painter.setPen(QPen(QColor(255, 255, 255, 120), 1.2))
                painter.setBrush(QBrush(QColor(255, 255, 255, 45)))
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(255, 255, 255, 18)))

            painter.drawRoundedRect(tile_rect, 9.0, 9.0)

            app_name = win.get("app_name", "")
            pix = self.tracker.get_app_icon(app_name, allow_generate=False)
            if pix and not pix.isNull():
                painter.drawPixmap(int(tile_rect.left() + 6.0), int(tile_rect.top() + 6.0), 24, 24, pix)
            else:
                painter.setPen(Config.COLOR_TEXT_PRIMARY)
                font_let = QFont("Segoe UI", 10, QFont.Weight.Bold)
                painter.setFont(font_let)
                let = (app_name[:1] if app_name else "A").upper()
                painter.drawText(tile_rect, Qt.AlignmentFlag.AlignCenter, let)

            if win.get("is_active"):
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(34, 197, 94)))
                painter.drawEllipse(QPointF(tile_rect.right() - 4.0, tile_rect.top() + 4.0), 3.0, 3.0)
            elif win.get("is_minimized"):
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(249, 115, 22)))
                painter.drawEllipse(QPointF(tile_rect.right() - 4.0, tile_rect.bottom() - 4.0), 2.5, 2.5)

        # 4. Label d'information de fenêtre
        label_x = dock_start_x + len(display_wins) * 44.0 + 8.0
        label_w = max(40.0, hub_rect.left() - label_x - 10.0)
        
        if hovered_win:
            is_act = hovered_win.get("is_active", False)
            is_min = hovered_win.get("is_minimized", False)
            status_str = "ACTIF" if is_act else ("RÉDUIT" if is_min else "OUVERT")
            status_col = QColor(34, 197, 94) if is_act else (QColor(249, 115, 22) if is_min else QColor(56, 189, 248))

            painter.setPen(Config.COLOR_TEXT_PRIMARY)
            font_t = QFont("Segoe UI", 8, QFont.Weight.Bold)
            painter.setFont(font_t)
            painter.drawText(
                QRectF(label_x, cy - 15.0, max(20.0, label_w - 60.0), 14.0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                hovered_win.get("app_name", "")
            )
            badge_r = QRectF(label_x + label_w - 56.0, cy - 14.0, 52.0, 13.0)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(status_col.red(), status_col.green(), status_col.blue(), 40)))
            painter.drawRoundedRect(badge_r, 6.0, 6.0)
            painter.setPen(status_col)
            painter.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
            painter.drawText(badge_r, Qt.AlignmentFlag.AlignCenter, status_str)

            painter.setPen(QColor(255, 255, 255, 210))
            font_sub = QFont("Segoe UI", 7, QFont.Weight.Normal)
            painter.setFont(font_sub)
            title = hovered_win.get("title", "")
            if len(title) > 35:
                title = title[:32] + "..."
            painter.drawText(
                QRectF(label_x, cy + 1.0, label_w, 14.0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                title
            )
        else:
            painter.setPen(QColor(255, 255, 255, 110))
            font_hint = QFont("Segoe UI", 8, QFont.Weight.Normal)
            painter.setFont(font_hint)
            nb = len(self.open_windows)
            status_txt = f"{nb} fenêtre{'s' if nb > 1 else ''} • Clic pour basculer" if nb > 0 else "Aucune fenêtre"
            painter.drawText(
                QRectF(label_x, cy - 9.0, label_w, 18.0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                status_txt
            )

    def _draw_control_hub_content(self, painter: QPainter, rect: QRectF):
        """
        Rendu du Super Hub de Contrôle (Hover intentionnel ou Clic sur bouton Agrandir) :
        - Bouton explicite 'Demander' avec microphone vectoriel pour poser toute question à la souris.
        - Bouton explicite de repli / fermeture sur le bord droit.
        - En-tête avec Actions Rapides vectorielles (Capture, Bureau, Réglages, Vider notifs).
        - Colonne gauche : Grille d'applications ouvertes.
        - Colonne droite : Historique des notifications.
        """
        acc = getattr(self, "accent_color", Config.COLOR_ACCENT_CYAN)

        # 1. En-tête & Titre
        dot_pos = QPointF(rect.left() + 20.0, rect.top() + 23.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(acc))
        painter.drawEllipse(dot_pos, 4.0, 4.0)

        font_head = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(font_head)
        painter.setPen(Config.COLOR_TEXT_PRIMARY)
        painter.drawText(
            QRectF(rect.left() + 30.0, rect.top() + 11.0, 140.0, 24.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "TABLEAU DE BORD"
        )

        btn_y = rect.top() + 11.0
        btn_h = 24.0

        # 2. Boutons tactiles Demander (Microphone) et Écrire (Clavier) dans l'en-tête
        ask_w = 84.0
        ask_x = rect.left() + 142.0
        self.btn_manual_ask_rect = QRectF(ask_x, btn_y, ask_w, btn_h)
        is_h_ask = (self.hovered_action_btn == "ask")
        if is_h_ask:
            painter.setPen(QPen(QColor(acc.red(), acc.green(), acc.blue(), 180), 1.0))
            painter.setBrush(QBrush(QColor(acc.red(), acc.green(), acc.blue(), 50)))
        else:
            painter.setPen(QPen(QColor(acc.red(), acc.green(), acc.blue(), 90), 1.0))
            painter.setBrush(QBrush(QColor(acc.red(), acc.green(), acc.blue(), 22)))
        painter.drawRoundedRect(self.btn_manual_ask_rect, 12.0, 12.0)
        draw_vector_microphone(painter, ask_x + 13.0, btn_y + 12.0, QColor(acc if is_h_ask else QColor(255, 255, 255, 230)), scale=0.8)
        painter.setPen(QColor(acc if is_h_ask else QColor(255, 255, 255, 230)))
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(QRectF(ask_x + 22.0, btn_y, ask_w - 26.0, btn_h), Qt.AlignmentFlag.AlignCenter, "Demander")

        # Bouton tactile Écrire / Clavier dans l'en-tête
        kb_w = 76.0
        kb_x = ask_x + ask_w + 6.0
        self.btn_keyboard_ask_rect = QRectF(kb_x, btn_y, kb_w, btn_h)
        is_h_kb = (self.hovered_action_btn == "keyboard_ask")
        if is_h_kb:
            painter.setPen(QPen(QColor(acc.red(), acc.green(), acc.blue(), 180), 1.0))
            painter.setBrush(QBrush(QColor(acc.red(), acc.green(), acc.blue(), 50)))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 45), 1.0))
            painter.setBrush(QBrush(QColor(255, 255, 255, 14)))
        painter.drawRoundedRect(self.btn_keyboard_ask_rect, 12.0, 12.0)
        draw_vector_keyboard(painter, kb_x + 13.0, btn_y + 12.0, QColor(acc if is_h_kb else QColor(255, 255, 255, 230)), scale=0.8)
        painter.setPen(QColor(acc if is_h_kb else QColor(255, 255, 255, 230)))
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(QRectF(kb_x + 22.0, btn_y, kb_w - 26.0, btn_h), Qt.AlignmentFlag.AlignCenter, "Écrire")

        # 3. Bouton tactile de REPLI / FERMETURE à l'extrémité droite
        col_w = 26.0
        col_x = rect.right() - col_w - 14.0
        self.btn_collapse_rect = QRectF(col_x, btn_y, col_w, btn_h)
        is_h_col = (self.hovered_action_btn == "collapse")
        painter.setPen(QPen(QColor(255, 255, 255, 80 if is_h_col else 30), 1.0))
        painter.setBrush(QBrush(QColor(255, 255, 255, 35 if is_h_col else 15)))
        painter.drawRoundedRect(self.btn_collapse_rect, 12.0, 12.0)
        draw_vector_expand_icon(painter, col_x + 13.0, btn_y + 12.0, QColor(255, 255, 255, 240 if is_h_col else 180), scale=0.9, is_expanded=True)

        # 4. Boutons d'actions rapides vectoriels (Screenshot, Bureau, Réglages, Vider notifs)
        # 4.1 Vider notifs
        self.btn_clear_notifs_rect = QRectF(col_x - 84.0, btn_y, 78.0, btn_h)
        is_h_clear = (self.hovered_action_btn == "clear_notifs")
        painter.setPen(QPen(QColor(255, 255, 255, 60 if is_h_clear else 25), 1.0))
        painter.setBrush(QBrush(QColor(255, 255, 255, 30 if is_h_clear else 14)))
        painter.drawRoundedRect(self.btn_clear_notifs_rect, 12.0, 12.0)
        draw_vector_trash(painter, self.btn_clear_notifs_rect.left() + 14.0, btn_y + 12.0, QColor(255, 255, 255, 220 if is_h_clear else 170), scale=0.8)
        painter.setPen(QColor(255, 255, 255, 220 if is_h_clear else 170))
        font_btn = QFont("Segoe UI", 7, QFont.Weight.Medium)
        painter.setFont(font_btn)
        painter.drawText(QRectF(self.btn_clear_notifs_rect.left() + 20.0, btn_y, 54.0, btn_h), Qt.AlignmentFlag.AlignCenter, "Effacer")

        # 4.2 Réglages
        self.btn_settings_rect = QRectF(self.btn_clear_notifs_rect.left() - 86.0, btn_y, 80.0, btn_h)
        is_h_set = (self.hovered_action_btn == "settings")
        painter.setPen(QPen(QColor(255, 255, 255, 60 if is_h_set else 25), 1.0))
        painter.setBrush(QBrush(QColor(255, 255, 255, 30 if is_h_set else 14)))
        painter.drawRoundedRect(self.btn_settings_rect, 12.0, 12.0)
        draw_vector_gear(painter, self.btn_settings_rect.left() + 14.0, btn_y + 12.0, QColor(255, 255, 255, 220 if is_h_set else 170), scale=0.8)
        painter.setPen(QColor(255, 255, 255, 220 if is_h_set else 170))
        painter.setFont(font_btn)
        painter.drawText(QRectF(self.btn_settings_rect.left() + 20.0, btn_y, 56.0, btn_h), Qt.AlignmentFlag.AlignCenter, "Réglages")

        # 4.3 Afficher Bureau
        self.btn_desktop_rect = QRectF(self.btn_settings_rect.left() - 78.0, btn_y, 72.0, btn_h)
        is_h_desk = (self.hovered_action_btn == "desktop")
        painter.setPen(QPen(QColor(255, 255, 255, 60 if is_h_desk else 25), 1.0))
        painter.setBrush(QBrush(QColor(255, 255, 255, 30 if is_h_desk else 14)))
        painter.drawRoundedRect(self.btn_desktop_rect, 12.0, 12.0)
        draw_vector_monitor(painter, self.btn_desktop_rect.left() + 14.0, btn_y + 12.0, QColor(255, 255, 255, 220 if is_h_desk else 170), scale=0.8)
        painter.setPen(QColor(255, 255, 255, 220 if is_h_desk else 170))
        painter.setFont(font_btn)
        painter.drawText(QRectF(self.btn_desktop_rect.left() + 20.0, btn_y, 48.0, btn_h), Qt.AlignmentFlag.AlignCenter, "Bureau")

        # 4.4 Screenshot
        self.btn_screenshot_rect = QRectF(self.btn_desktop_rect.left() - 86.0, btn_y, 80.0, btn_h)
        is_h_shot = (self.hovered_action_btn == "screenshot")
        painter.setPen(QPen(QColor(acc.red(), acc.green(), acc.blue(), 180 if is_h_shot else 90), 1.0))
        painter.setBrush(QBrush(QColor(acc.red(), acc.green(), acc.blue(), 45 if is_h_shot else 20)))
        painter.drawRoundedRect(self.btn_screenshot_rect, 12.0, 12.0)
        draw_vector_camera(painter, self.btn_screenshot_rect.left() + 14.0, btn_y + 12.0, QColor(acc if is_h_shot else QColor(255, 255, 255, 220)), scale=0.8)
        painter.setPen(QColor(acc if is_h_shot else QColor(255, 255, 255, 220)))
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(QRectF(self.btn_screenshot_rect.left() + 20.0, btn_y, 56.0, btn_h), Qt.AlignmentFlag.AlignCenter, "Capture")

        # Ligne séparatrice
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
        painter.drawLine(QPointF(rect.left() + 18.0, rect.top() + 42.0), QPointF(rect.right() - 18.0, rect.top() + 42.0))

        # 5. Corps principal : Deux Colonnes
        content_top = rect.top() + 48.0
        col1_w = 415.0
        col2_x = rect.left() + col1_w + 14.0
        col2_w = rect.right() - col2_x - 16.0

        # Séparateur vertical entre colonnes
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        painter.drawLine(QPointF(col2_x - 7.0, content_top + 4.0), QPointF(col2_x - 7.0, rect.bottom() - 14.0))

        # --- COLONNE 1 : APPLICATIONS OUVERTES ---
        painter.setPen(QColor(255, 255, 255, 150))
        font_sec = QFont("Segoe UI", 7, QFont.Weight.Bold)
        painter.setFont(font_sec)
        painter.drawText(
            QRectF(rect.left() + 18.0, content_top, col1_w, 16.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            f"APPLICATIONS OUVERTES ({len(self.open_windows)})"
        )

        grid_top = content_top + 20.0
        card_w = (col1_w - 10.0) / 2.0  # ~202px
        card_h = 56.0
        self.hub_app_rects = []
        display_apps = self.open_windows[:6]  # 6 cartes en grille (2 cols x 3 lignes)

        for i, win in enumerate(display_apps):
            row = i // 2
            col = i % 2
            cx = rect.left() + 18.0 + col * (card_w + 8.0)
            cy = grid_top + row * (card_h + 8.0)
            card_rect = QRectF(cx, cy, card_w, card_h)
            self.hub_app_rects.append(card_rect)

            is_app_hovered = (i == self.hovered_hub_app)
            if is_app_hovered:
                painter.setPen(QPen(QColor(acc.red(), acc.green(), acc.blue(), 180), 1.2))
                painter.setBrush(QBrush(QColor(255, 255, 255, 32)))
            else:
                painter.setPen(QPen(QColor(255, 255, 255, 22), 1.0))
                painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
            painter.drawRoundedRect(card_rect, 10.0, 10.0)

            # Icône de l'application
            pix = self.tracker.get_app_icon(win.get("app_name", ""), allow_generate=False)
            if pix and not pix.isNull():
                painter.drawPixmap(int(cx + 8.0), int(cy + 14.0), 28, 28, pix)
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(255, 255, 255, 25)))
                painter.drawRoundedRect(QRectF(cx + 8.0, cy + 14.0, 28.0, 28.0), 6.0, 6.0)
                painter.setPen(Config.COLOR_TEXT_PRIMARY)
                painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                let = (win.get("app_name", "A")[:1]).upper()
                painter.drawText(QRectF(cx + 8.0, cy + 14.0, 28.0, 28.0), Qt.AlignmentFlag.AlignCenter, let)

            # Titre & App Name
            text_x = cx + 42.0
            text_w = card_w - 48.0 - 44.0  # réserve espace pour badge

            painter.setPen(Config.COLOR_TEXT_PRIMARY)
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(
                QRectF(text_x, cy + 10.0, text_w, 16.0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                win.get("app_name", "")
            )

            painter.setPen(Config.COLOR_TEXT_SECONDARY)
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Normal))
            raw_title = win.get("title", "")
            if len(raw_title) > 20:
                raw_title = raw_title[:18] + "..."
            painter.drawText(
                QRectF(text_x, cy + 28.0, text_w + 40.0, 16.0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                raw_title
            )

            # Badge de statut (Actif / Réduit / Ouvert)
            badge_w = 38.0
            badge_h = 14.0
            badge_rect = QRectF(card_rect.right() - badge_w - 6.0, cy + 8.0, badge_w, badge_h)
            painter.setPen(Qt.PenStyle.NoPen)
            if win.get("is_active"):
                painter.setBrush(QBrush(QColor(34, 197, 94, 45)))
                painter.drawRoundedRect(badge_rect, 7.0, 7.0)
                painter.setPen(QColor(34, 197, 94))
                painter.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "ACTIF")
            elif win.get("is_minimized"):
                painter.setBrush(QBrush(QColor(249, 115, 22, 45)))
                painter.drawRoundedRect(badge_rect, 7.0, 7.0)
                painter.setPen(QColor(249, 115, 22))
                painter.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "RÉDUIT")
            else:
                painter.setBrush(QBrush(QColor(255, 255, 255, 18)))
                painter.drawRoundedRect(badge_rect, 7.0, 7.0)
                painter.setPen(QColor(255, 255, 255, 140))
                painter.setFont(QFont("Segoe UI", 6, QFont.Weight.Normal))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "OUVERT")

        # --- COLONNE 2 : TOUTES LES NOTIFICATIONS ---
        painter.setPen(QColor(255, 255, 255, 150))
        painter.setFont(font_sec)
        painter.drawText(
            QRectF(col2_x, content_top, col2_w, 16.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            f"NOTIFICATIONS ({len(self.notif_mgr.items)})"
        )

        self.hub_notif_rects = []
        if len(self.notif_mgr.items) == 0:
            painter.setPen(QColor(255, 255, 255, 80))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
            painter.drawText(
                QRectF(col2_x, content_top + 50.0, col2_w, 40.0),
                Qt.AlignmentFlag.AlignCenter,
                "Aucune notification récente\nVotre flux est à jour."
            )
        else:
            notif_card_h = 56.0
            display_notifs = self.notif_mgr.items[:3]  # Jusqu'à 3 cartes de notifications
            for j, item in enumerate(display_notifs):
                ny = grid_top + j * (notif_card_h + 8.0)
                n_rect = QRectF(col2_x, ny, col2_w, notif_card_h)
                self.hub_notif_rects.append(n_rect)

                is_n_h = (j == self.hovered_hub_notif)
                painter.setPen(QPen(QColor(255, 255, 255, 45 if is_n_h else 20), 1.0))
                painter.setBrush(QBrush(QColor(255, 255, 255, 24 if is_n_h else 12)))
                painter.drawRoundedRect(n_rect, 10.0, 10.0)

                # Logo / Icône de l'application notificatrice
                if item.logo and not item.logo.isNull():
                    painter.drawPixmap(int(col2_x + 8.0), int(ny + 14.0), 24, 24, item.logo)
                else:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(QColor(item.color_hex)))
                    painter.drawRoundedRect(QRectF(col2_x + 8.0, ny + 14.0, 24.0, 24.0), 6.0, 6.0)
                    painter.setPen(QColor(255, 255, 255))
                    painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    painter.drawText(QRectF(col2_x + 8.0, ny + 14.0, 24.0, 24.0), Qt.AlignmentFlag.AlignCenter, item.app_name[:1].upper())

                # Textes de la notification
                nt_x = col2_x + 38.0
                nt_w = col2_w - 44.0
                painter.setPen(QColor(item.color_hex))
                painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                painter.drawText(
                    QRectF(nt_x, ny + 8.0, nt_w, 14.0),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    f"{item.app_name.upper()}  •  {item.time_str}"
                )

                painter.setPen(Config.COLOR_TEXT_PRIMARY)
                painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                title_s = item.title if item.title else item.app_name
                if len(title_s) > 24:
                    title_s = title_s[:22] + "..."
                painter.drawText(
                    QRectF(nt_x, ny + 22.0, nt_w, 14.0),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    title_s
                )

                painter.setPen(Config.COLOR_TEXT_SECONDARY)
                painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Normal))
                msg_s = item.message
                if len(msg_s) > 30:
                    msg_s = msg_s[:28] + "..."
                painter.drawText(
                    QRectF(nt_x, ny + 36.0, nt_w, 14.0),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    msg_s
                )

    def _draw_prompt_input_content(self, painter: QPainter, rect: QRectF):
        """Rendu du champ de saisie de prompt au clavier avec esthétique Obsidian Apple Glass."""
        cy = rect.center().y()
        acc = getattr(self, "accent_color", Config.COLOR_ACCENT_CYAN)

        # 1. Bordure d'accentuation subtile (Glow hairline cyan)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        glow_pen = QPen(QColor(acc.red(), acc.green(), acc.blue(), 140), 1.0)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        radius = min(self.cur_r, self.cur_h / 2.0)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        painter.restore()

        # 2. Icône de clavier vectorielle à gauche
        kb_icon_x = rect.left() + 24.0
        draw_vector_keyboard(painter, kb_icon_x, cy, acc, scale=1.0)

        # 3. Séparateur vertical fin
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        painter.drawLine(QPointF(rect.left() + 42.0, cy - 10.0), QPointF(rect.left() + 42.0, cy + 10.0))

        # 4. Positionnement dynamique du QLineEdit enfant au centre
        input_x = rect.left() + 48.0
        btn_group_w = 64.0
        input_w = max(100.0, rect.width() - 48.0 - btn_group_w - 12.0)
        input_h = 28.0
        input_y = cy - input_h / 2.0

        geom = QRect(int(input_x), int(input_y), int(input_w), int(input_h))
        if self.prompt_input.geometry() != geom:
            self.prompt_input.setGeometry(geom)
        if not self.prompt_input.isVisible():
            self.prompt_input.show()
            self.prompt_input.setFocus()

        # 5. Bouton Envoi (Flèche vectorielle vers le haut / droite)
        btn_send_w = 26.0
        btn_send_h = 26.0
        btn_send_x = rect.right() - 64.0
        btn_send_y = cy - btn_send_h / 2.0
        self.btn_prompt_send_rect = QRectF(btn_send_x, btn_send_y, btn_send_w, btn_send_h)

        has_text = bool(self.prompt_input.text().strip())
        is_h_send = (self.hovered_action_btn == "prompt_send")

        if has_text:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(acc if not is_h_send else QColor(acc.red(), acc.green(), acc.blue(), 220)))
            painter.drawRoundedRect(self.btn_prompt_send_rect, 13.0, 13.0)
            draw_vector_send(painter, self.btn_prompt_send_rect.center().x(), cy, QColor(10, 10, 14), scale=0.85)
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 40 if is_h_send else 20), 1.0))
            painter.setBrush(QBrush(QColor(255, 255, 255, 25 if is_h_send else 10)))
            painter.drawRoundedRect(self.btn_prompt_send_rect, 13.0, 13.0)
            draw_vector_send(painter, self.btn_prompt_send_rect.center().x(), cy, QColor(255, 255, 255, 160 if is_h_send else 90), scale=0.85)

        # 6. Bouton Annuler / Fermer (Croix vectorielle ✕)
        btn_cancel_w = 24.0
        btn_cancel_h = 24.0
        btn_cancel_x = rect.right() - 32.0
        btn_cancel_y = cy - btn_cancel_h / 2.0
        self.btn_prompt_cancel_rect = QRectF(btn_cancel_x, btn_cancel_y, btn_cancel_w, btn_cancel_h)

        is_h_cancel = (self.hovered_action_btn == "prompt_cancel")
        painter.setPen(QPen(QColor(255, 255, 255, 50 if is_h_cancel else 20), 1.0))
        painter.setBrush(QBrush(QColor(255, 255, 255, 30 if is_h_cancel else 10)))
        painter.drawRoundedRect(self.btn_prompt_cancel_rect, 12.0, 12.0)
        draw_vector_close(painter, self.btn_prompt_cancel_rect.center().x(), cy, QColor(255, 255, 255, 220 if is_h_cancel else 130), scale=0.85)
