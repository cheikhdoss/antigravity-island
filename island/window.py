import sys
import math
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QTimer, QVariantAnimation, QEasingCurve, pyqtSignal
)
from PyQt6.QtWidgets import QWidget, QApplication, QMenu
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QPainterPath, QRadialGradient
)

from island.config import Config
from island.components.waveform import WaveformVisualizer
from island.components.glowing_orb import GlowingOrb
from island.pointer import PointerOverlay
from island.voice import VoiceEngine

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

class IslandWindow(QWidget):
    """
    Fenêtre principale de l'encoche dynamique Antigravity.
    Supporte à la fois le style Dynamic Island (pilule) et l'encoche iPhone X (notch avec cornes).
    Collée au plus près du bord supérieur de l'écran Windows, sans bordure et ultra-fluide.
    """
    
    state_change_requested = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.current_state = "idle"
        cfg = Config.STATES[self.current_state]
        
        self.custom_idle_w = 120.0
        self.custom_idle_h = 32.0
        
        self.cur_w = float(self.custom_idle_w)
        self.cur_h = float(self.custom_idle_h)
        self.cur_r = float(self.custom_idle_h / 2.0)
        self.target_w = self.cur_w
        self.target_h = self.cur_h
        self.target_r = self.cur_r

        # Paramètres de disposition et style
        self.style_mode = "island"      # "island" (pilule) ou "iphonex" (encoche iPhone X)
        self.position_mode = "notch"   # "notch" (collé au header à Y=0) ou "floating"
        self.alignment = "center"       # "center", "left", "right"
        self.screen_index = 0           # Index de l'écran cible (Multi-Moniteurs)
        self.top_margin = 0
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

        # Composants vocaux et contrôle
        self.settings_window = None
        self.voice_enabled = True
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

        self.state_change_requested.connect(self.apply_remote_command)
        self._update_geometry()

    def apply_settings(self, settings: dict):
        if "accent_color" in settings:
            self.accent_color = QColor(settings["accent_color"])
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
        elif action == "speak":
            self.message_text = data.get("text", "")
            self.set_state("speaking", data)
            if getattr(self, "voice_enabled", True):
                import time
                def on_done():
                    time.sleep(1.2)
                    self.state_change_requested.emit("idle", {})
                self.voice_engine.speak(self.message_text, callback_on_finish=on_done)
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
        elif action == "point_at":
            x = data.get("x", 500)
            y = data.get("y", 300)
            label = data.get("label", "")
            duration = float(data.get("duration", 3.5))
            color = data.get("color", None)
            self.pointer.point_at(x, y, label, duration, color)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # En mode réel : clic gauche ouvre / met en avant le Centre de contrôle
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
        bg_grad.setColorAt(0.0, QColor(14, 14, 18, 252))
        bg_grad.setColorAt(1.0, QColor(6, 6, 8, 255))
        painter.fillPath(main_path, QBrush(bg_grad))

        # 3. Bordure subtile Hairline
        border_pen = QPen(Config.COLOR_BORDER, 1.0)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(main_path)

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

    def _draw_idle_content(self, painter: QPainter, rect: QRectF):
        """Contenu compact au repos — Point lumineux positionné strictement à GAUCHE."""
        cy = rect.center().y()
        if self.style_mode == "iphonex":
            cy += 2.0  # Légère compensation sous la grille haut-parleur
            
        dot_x = rect.left() + min(18.0, rect.height() * 0.65)
        dot_pos = QPointF(dot_x, cy)
        acc = getattr(self, "accent_color", Config.COLOR_ACCENT_CYAN)
        
        # Halo lumineux doux à gauche
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

        # Pastille lumineuse compacte à gauche
        painter.setBrush(QBrush(acc))
        painter.drawEllipse(dot_pos, 3.2, 3.2)

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
