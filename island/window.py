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

        # Suivi des fenêtres réduites (Dock Dynamic Island)
        self.tracker = MinimizedWindowTracker()
        self.minimized_windows = []
        self.hovered_dock_index = -1
        self.minimized_timer = QTimer(self)
        self.minimized_timer.timeout.connect(self._check_minimized_windows)
        self.minimized_timer.start(400)

        # Gestionnaire de notifications & historique carrousel
        self.notif_mgr = NotificationManager(max_items=50)
        self.notif_btn_clear_rect = QRectF()
        self.notif_btn_prev_rect = QRectF()
        self.notif_btn_next_rect = QRectF()

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
        elif state_name == "notification":
            self.target_w = 460.0
            self.target_h = 76.0
            self.target_r = 26.0
        elif state_name == "minimized_dock":
            self.target_w = max(280.0, 70.0 + len(self.minimized_windows) * 44.0)
            self.target_h = 54.0
            self.target_r = 24.0
        elif state_name == "thinking":
            target_cfg = Config.STATES[state_name]
            title = getattr(self, "action_title", "") or ""
            if title and title != "Analyse en cours...":
                self.target_w = max(float(target_cfg.width), min(450.0, 90.0 + len(title) * 8.5))
            else:
                self.target_w = float(target_cfg.width)
            self.target_h = float(target_cfg.height)
            self.target_r = float(target_cfg.radius)
        else:
            target_cfg = Config.STATES[state_name]
            self.target_w = float(target_cfg.width)
            self.target_h = float(target_cfg.height)
            self.target_r = float(target_cfg.radius)
        
        if state_name in ["speaking", "action", "notification", "minimized_dock"]:
            self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim.setDuration(340)
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
                # Règle UX stricte demandée par l'utilisateur :
                # 1. Affirmation/statut court de l'Island (ex: "Je suis prêt", "Microphone inaudible", "Pas bien compris") -> 2 secondes (2000 ms)
                # 2. Réponse substantielle à une requête -> Reste affichée plus de 5s pour permettre la lecture (base 7s + 50ms/caractère, max 25s)
                txt_lower = self.message_text.lower().strip()
                is_status = data.get("is_status", False) or any(kw in txt_lower for kw in [
                    "inaudible", "pas bien compris", "suis prêt", "suis pret", "à votre écoute",
                    "a votre ecoute", "analys", "réessayez", "reessayez", "parlez un peu plus",
                    "prêt !", "pret !"
                ]) and not data.get("is_answer", False)

                if is_status or (len(self.message_text) <= 45 and not data.get("is_answer", False)):
                    reading_ms = 2000  # 2 secondes pile pour les affirmations/statuts du island
                else:
                    # Plus de 5 secondes pour une vraie réponse à une requête
                    reading_ms = int(max(7000, min(25000, 6500 + len(self.message_text) * 50)))

                self.reading_timer.start(reading_ms)
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

    def _check_minimized_windows(self):
        try:
            wins = self.tracker.get_minimized_windows()
            prev_count = len(self.minimized_windows)
            self.minimized_windows = wins
            if len(wins) != prev_count:
                if self.current_state == "minimized_dock":
                    if len(wins) == 0:
                        self.set_state("idle")
                    else:
                        new_w = max(280.0, 70.0 + len(wins) * 44.0)
                        self.target_w = new_w
                        self.anim.stop()
                        self.cur_w = new_w
                        self._update_geometry()
                self.update()
        except Exception:
            pass

    def enterEvent(self, event):
        super().enterEvent(event)
        if self.current_state == "idle" and len(self.minimized_windows) > 0:
            self.set_state("minimized_dock")

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.hovered_dock_index = -1
        if self.current_state == "minimized_dock":
            self.set_state("idle")

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.current_state == "minimized_dock":
            pos = event.position()
            pad_x = Config.SHADOW_BLUR + 16.0
            dock_x = pad_x + 18.0
            cy = self.height() / 2.0
            hovered = -1
            for i in range(len(self.minimized_windows)):
                tile_rect = QRectF(dock_x + i * 44.0, cy - 18.0, 36.0, 36.0)
                if tile_rect.contains(pos):
                    hovered = i
                    break
            if hovered != self.hovered_dock_index:
                self.hovered_dock_index = hovered
                self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.current_state == "minimized_dock":
                if 0 <= self.hovered_dock_index < len(self.minimized_windows):
                    win = self.minimized_windows[self.hovered_dock_index]
                    self.tracker.restore_window(win["hwnd"])
                    self._check_minimized_windows()
                    self.set_state("idle")
                    return
            elif self.current_state == "notification":
                pos = event.position()
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
        elif self.current_state == "notification":
            self._draw_notification_content(painter, pill_rect)
        elif self.current_state == "minimized_dock":
            self._draw_minimized_dock_content(painter, pill_rect)

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

        # Indicateur discret de fenêtres minimisées à droite (si présentes)
        if len(self.minimized_windows) > 0:
            count = len(self.minimized_windows)
            badge_x = rect.right() - 28.0
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 25)))
            painter.drawRoundedRect(QRectF(badge_x, cy - 7.0, 18.0, 14.0), 7.0, 7.0)
            painter.setPen(QColor(255, 255, 255, 170))
            font_cnt = QFont("Segoe UI", 7, QFont.Weight.Bold)
            painter.setFont(font_cnt)
            painter.drawText(QRectF(badge_x, cy - 7.0, 18.0, 14.0), Qt.AlignmentFlag.AlignCenter, str(count))

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
        label = getattr(self, "action_title", "") or "Analyse en cours..."
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)

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
            painter.setPen(QColor(255, 255, 255, 90))
            font_sub = QFont("Segoe UI", 8, QFont.Weight.Medium)
            painter.setFont(font_sub)
            painter.drawText(
                QRectF(rect.right() - 90.0, header_y - 8.0, 70.0, 16.0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                "Dynamic Island"
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
        pad_left = rect.left() + 18.0
        cy = rect.center().y()

        hovered_win = None
        for i, win in enumerate(self.minimized_windows):
            tile_x = pad_left + i * 44.0
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

            # Dessin de l'icône de l'application
            pix = win.get("pixmap")
            if pix and not pix.isNull():
                painter.drawPixmap(int(tile_rect.left() + 6.0), int(tile_rect.top() + 6.0), 24, 24, pix)
            else:
                painter.setPen(Config.COLOR_TEXT_PRIMARY)
                font_let = QFont("Segoe UI", 10, QFont.Weight.Bold)
                painter.setFont(font_let)
                let = (win.get("app_name", "A")[:1]).upper()
                painter.drawText(tile_rect, Qt.AlignmentFlag.AlignCenter, let)

        # Label d'information sur la droite des tuiles
        label_x = pad_left + len(self.minimized_windows) * 44.0 + 8.0
        label_w = max(40.0, rect.right() - label_x - 12.0)
        
        if hovered_win:
            painter.setPen(Config.COLOR_TEXT_PRIMARY)
            font_t = QFont("Segoe UI", 8, QFont.Weight.Medium)
            painter.setFont(font_t)
            title = hovered_win.get("title", "")
            if len(title) > 22:
                title = title[:19] + "..."
            painter.drawText(
                QRectF(label_x, cy - 14.0, label_w, 14.0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                hovered_win.get("app_name", "")
            )
            painter.setPen(Config.COLOR_TEXT_SECONDARY)
            font_sub = QFont("Segoe UI", 7, QFont.Weight.Normal)
            painter.setFont(font_sub)
            painter.drawText(
                QRectF(label_x, cy, label_w, 14.0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                title
            )
        else:
            painter.setPen(QColor(255, 255, 255, 100))
            font_hint = QFont("Segoe UI", 8, QFont.Weight.Normal)
            painter.setFont(font_hint)
            painter.drawText(
                QRectF(label_x, cy - 9.0, label_w, 18.0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                f"{len(self.minimized_windows)} réduite{'s' if len(self.minimized_windows) > 1 else ''}"
            )
