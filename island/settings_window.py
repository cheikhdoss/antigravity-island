import sys
import json
import os
import winreg
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QSlider, QComboBox, QSystemTrayIcon, QMenu, QColorDialog, QScrollArea, QCheckBox, QLineEdit
)
from PyQt6.QtGui import QIcon, QColor, QFont, QPixmap, QPainter, QBrush

from island.config import Config

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "AntigravityIsland"

def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except Exception:
        return False

def set_autostart(enable: bool) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                if getattr(sys, "frozen", False):
                    exe_path = sys.executable
                else:
                    desktop_exe = os.path.join(os.path.expanduser("~"), "Desktop", "AntigravityIsland", "AntigravityIsland.exe")
                    if os.path.exists(desktop_exe):
                        exe_path = desktop_exe
                    else:
                        exe_path = os.path.abspath(sys.argv[0])
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
                print(f"[Autostart] Enregistre dans Windows Run : {exe_path}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    print("[Autostart] Supprime de Windows Run")
                except FileNotFoundError:
                    pass
            return True
    except Exception as e:
        print("[Autostart] Erreur registre Windows :", e)
        return False

def get_settings_file_path():
    """Chemin de configuration permanent et persistant dans le profil utilisateur Windows."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = os.path.expanduser("~")
    settings_dir = os.path.join(appdata, "AntigravityIsland")
    os.makedirs(settings_dir, exist_ok=True)
    return os.path.join(settings_dir, "settings.json")

def load_settings():
    default_settings = {
        "accent_color": "#38bdf8",
        "island_bg_color": "#08080a",
        "style_mode": "island",      # "island" (pilule) ou "iphonex" (encoche iPhone X)
        "position_mode": "notch",   # "notch" (collé au bord) ou "floating"
        "alignment": "center",       # "center", "left", "right"
        "idle_width": 110,           # Largeur au repos
        "idle_height": 30,           # Hauteur au repos
        "island_visible": True,
        "ptt_mode": "hold",          # "hold" (Push-to-talk immédiat), "hybrid", "toggle"
        "voice_enabled": False,      # Texte pur sur le Dynamic Island (sans voix)
        "voice_name": "fr-FR-VivienneMultilingualNeural",
        "voice_rate": "+10%",
        "llm_provider": "agnes",     # "agnes" (Agnes AI 3.0 Flash), "gemini", "nim" (NVIDIA NIM), "agy" (AGY CLI ACP)
        "nim_model": "nvidia/nemotron-3.5-bolt-e4b",
        "agy_model": "gemini-3.8-flash",  # "gemini-3.8-flash", "claude-sonnet-4-6", "claude-opus-4-6-thinking", "gpt-oss-120b-medium"
        "agy_thought_level": "low",       # "low" (instantané), "medium", "high"
        "vision_provider": "agnes",   # "agnes", "gemini_vl", "agy_vl", "nim_vl", "ocr"
        "gemini_api_key": "",         # Clé API Google Gemini pour requêtes directes
        "stt_provider": "antigravity", # "antigravity" (DeepMind Connect-RPC), "google", "offline"
        "autostart": is_autostart_enabled(),
        "screen_index": 0,
        "hide_on_screen_share": True,  # Mode furtif WDA pour visioconférences (Google Meet, Zoom, Teams)
        "meet_mode_enabled": False,    # Assistant de cours en direct (WASAPI Loopback)
        "meet_audio_source": "loopback", # "loopback" (Haut-parleurs WASAPI seuls) ou "hybrid" (Micro + HP)
    }
    settings_path = get_settings_file_path()
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    default_settings.update(data)
                print(f"[Settings] Paramètres chargés avec succès depuis {settings_path}")
        except Exception as e:
            print("[Settings] Erreur lecture settings:", e)
    else:
        save_settings(default_settings)
    return default_settings

def save_settings(settings):
    """Sauvegarde atomique et garantie sans perte de données sur disque."""
    try:
        settings_path = get_settings_file_path()
        tmp_path = settings_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, settings_path)
        print(f"[Settings] Paramètres enregistrés dans {settings_path}")
    except Exception as e:
        print("[Settings] Erreur sauvegarde settings:", e)

class SettingsWindow(QWidget):
    """
    Panneau de contrôle & Paramètres pour Antigravity Island.
    Gère la taille, l'accrochage au header (Y=0), l'alignement et les couleurs.
    """
    settings_changed = pyqtSignal(dict)
    state_trigger_requested = pyqtSignal(str)
    toggle_island_requested = pyqtSignal(bool)

    def __init__(self, island_window=None):
        super().__init__()
        self.island_window = island_window
        self.settings = load_settings()

        self.setWindowTitle("Antigravity Control Center")
        self.setFixedSize(660, 880)
        self.setStyleSheet("""
            QWidget {
                background-color: #0b0f19;
                color: #f1f5f9;
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            }
            QFrame.card {
                background-color: #131b2e;
                border: 1px solid #1e293b;
                border-radius: 12px;
                padding: 14px;
            }
            QLabel.title {
                font-size: 18px;
                font-weight: 700;
                color: #ffffff;
            }
            QLabel.subtitle {
                font-size: 12px;
                color: #94a3b8;
            }
            QLabel.section {
                font-size: 12px;
                font-weight: 700;
                color: #38bdf8;
                text-transform: uppercase;
                letter-spacing: 0.6px;
            }
            QPushButton.primary {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: 600;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 9px 16px;
            }
            QPushButton.primary:hover {
                background-color: #0369a1;
            }
            QPushButton.secondary {
                background-color: #1e293b;
                color: #e2e8f0;
                font-weight: 500;
                font-size: 12px;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton.secondary:hover {
                background-color: #334155;
                border-color: #475569;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #1e293b;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #38bdf8;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid #0284c7;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
            QComboBox {
                background-color: #1e293b;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 12px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                min-width: 220px;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
            }
            QComboBox:hover {
                border-color: #38bdf8;
                background-color: #243247;
            }
            QComboBox:focus {
                border-color: #38bdf8;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border-left: 1px solid #475569;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #1e293b;
            }
            QComboBox::down-arrow {
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #38bdf8;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #ffffff;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 28px;
                padding: 4px 8px;
                color: #ffffff;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QScrollBar:vertical {
                border: none;
                background: #0b0f19;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #475569;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 16)
        main_layout.setSpacing(12)

        # En-tête (Fixe)
        header_layout = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("Antigravity Control Center")
        title.setProperty("class", "title")
        subtitle = QLabel("Design & Disposition de l'encoche")
        subtitle.setProperty("class", "subtitle")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        self.saved_badge = QLabel("✓ Paramètres synchronisés")
        self.saved_badge.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 500; padding-right: 6px;")
        header_layout.addWidget(self.saved_badge)

        status_badge = QLabel("  ● Actif (8765)  ")
        status_badge.setStyleSheet("background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; font-size: 11px; font-weight: 600; padding: 4px 8px;")
        header_layout.addWidget(status_badge)
        main_layout.addLayout(header_layout)

        # Zone défilante (Scrollable) pour garantir l'accessibilité sur tous les écrans
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(12)

        # CARTE 1 : Disposition & Accrochage au Header
        card_disp = QFrame()
        card_disp.setProperty("class", "card")
        layout_disp = QVBoxLayout(card_disp)
        layout_disp.setSpacing(10)

        lbl_disp = QLabel("Disposition & Fixation au Header")
        lbl_disp.setProperty("class", "section")
        layout_disp.addWidget(lbl_disp)

        # Style de l'encoche (Dynamic Island vs Encoche iPhone X)
        row_style = QHBoxLayout()
        row_style.addWidget(QLabel("Style de l'encoche :"))
        row_style.addStretch()
        self.combo_style = QComboBox()
        self.combo_style.blockSignals(True)
        self.combo_style.addItems(["Dynamic Island (Pilule moderne)", "Encoche iPhone X (Notch avec cornes)"])
        self.combo_style.setCurrentIndex(1 if self.settings.get("style_mode") == "iphonex" else 0)
        self.combo_style.blockSignals(False)
        self.combo_style.currentIndexChanged.connect(self._on_style_changed)
        row_style.addWidget(self.combo_style)
        layout_disp.addLayout(row_style)

        # Accrochage au bord (Notch collé vs Flottant)
        row_pos = QHBoxLayout()
        row_pos.addWidget(QLabel("Fixation :"))
        row_pos.addStretch()
        self.combo_mode = QComboBox()
        self.combo_mode.blockSignals(True)
        self.combo_mode.addItems(["Collé au plus près du bord (Notch Y=0)", "Flottant (Capsule détachée)"])
        self.combo_mode.setCurrentIndex(1 if self.settings.get("position_mode") == "floating" else 0)
        self.combo_mode.blockSignals(False)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        row_pos.addWidget(self.combo_mode)
        layout_disp.addLayout(row_pos)

        # Alignement Horizontal
        row_align = QHBoxLayout()
        row_align.addWidget(QLabel("Alignement :"))
        row_align.addStretch()
        self.combo_align = QComboBox()
        self.combo_align.blockSignals(True)
        self.combo_align.addItems(["Centre (Recommandé)", "Gauche", "Droite"])
        cur_align = self.settings.get("alignment", "center")
        if cur_align == "left":
            self.combo_align.setCurrentIndex(1)
        elif cur_align == "right":
            self.combo_align.setCurrentIndex(2)
        else:
            self.combo_align.setCurrentIndex(0)
        self.combo_align.blockSignals(False)
        self.combo_align.currentIndexChanged.connect(self._on_align_changed)
        row_align.addWidget(self.combo_align)
        layout_disp.addLayout(row_align)

        # Choix de l'Écran (Multi-Moniteurs)
        row_screen = QHBoxLayout()
        row_screen.addWidget(QLabel("Écran d'affichage :"))
        row_screen.addStretch()
        self.combo_screen = QComboBox()
        self.combo_screen.blockSignals(True)
        screens = QApplication.screens()
        for i, sc in enumerate(screens):
            geo = sc.geometry()
            self.combo_screen.addItem(f"Écran {i+1} ({geo.width()}x{geo.height()})")
        cur_sc = int(self.settings.get("screen_index", 0))
        if 0 <= cur_sc < len(screens):
            self.combo_screen.setCurrentIndex(cur_sc)
        self.combo_screen.blockSignals(False)
        self.combo_screen.currentIndexChanged.connect(self._on_screen_changed)
        row_screen.addWidget(self.combo_screen)
        layout_disp.addLayout(row_screen)

        content_layout.addWidget(card_disp)

        # CARTE 2 : Dimension de l'encoche
        card_size = QFrame()
        card_size.setProperty("class", "card")
        layout_size = QVBoxLayout(card_size)
        layout_size.setSpacing(10)

        lbl_size = QLabel("Taille de l'Encoche au Repos")
        lbl_size.setProperty("class", "section")
        layout_size.addWidget(lbl_size)

        # Largeur (Slider)
        layout_w = QHBoxLayout()
        layout_w.addWidget(QLabel("Largeur :"))
        self.lbl_w_val = QLabel(f"{int(self.settings.get('idle_width', 110))} px")
        self.lbl_w_val.setStyleSheet("color: #38bdf8; font-weight: bold; width: 45px;")
        layout_w.addWidget(self.lbl_w_val)
        self.slider_w = QSlider(Qt.Orientation.Horizontal)
        self.slider_w.setRange(70, 220)
        self.slider_w.blockSignals(True)
        self.slider_w.setValue(int(self.settings.get("idle_width", 110)))
        self.slider_w.blockSignals(False)
        self.slider_w.valueChanged.connect(self._on_width_changed)
        layout_w.addWidget(self.slider_w)
        layout_size.addLayout(layout_w)

        # Hauteur (Slider)
        layout_h = QHBoxLayout()
        layout_h.addWidget(QLabel("Hauteur :"))
        self.lbl_h_val = QLabel(f"{int(self.settings.get('idle_height', 30))} px")
        self.lbl_h_val.setStyleSheet("color: #38bdf8; font-weight: bold; width: 45px;")
        layout_h.addWidget(self.lbl_h_val)
        self.slider_h = QSlider(Qt.Orientation.Horizontal)
        self.slider_h.setRange(22, 45)
        self.slider_h.blockSignals(True)
        self.slider_h.setValue(int(self.settings.get("idle_height", 30)))
        self.slider_h.blockSignals(False)
        self.slider_h.valueChanged.connect(self._on_height_changed)
        layout_h.addWidget(self.slider_h)
        layout_size.addLayout(layout_h)

        content_layout.addWidget(card_size)

        # CARTE 3 : Personnalisation Couleurs & Test
        card_style = QFrame()
        card_style.setProperty("class", "card")
        layout_style = QVBoxLayout(card_style)
        layout_style.setSpacing(10)

        lbl_style = QLabel("Couleurs & Tests Rapides")
        lbl_style.setProperty("class", "section")
        layout_style.addWidget(lbl_style)

        # Palette
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Couleur d'accent :"))
        color_row.addStretch()

        presets = [
            ("#38bdf8", "Cyan"),
            ("#22c55e", "Émeraude"),
            ("#a855f7", "Améthyste"),
            ("#f97316", "Orange"),
            ("#f43f5e", "Rose"),
            ("#ffffff", "Blanc")
        ]
        for hex_code, name in presets:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setProperty("class", "accent-btn")
            btn.setToolTip(name)
            btn.setStyleSheet(f"background-color: {hex_code}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);")
            btn.clicked.connect(lambda checked, c=hex_code: self._set_accent_color(c))
            color_row.addWidget(btn)

        btn_pick = QPushButton("Libre...")
        btn_pick.setProperty("class", "secondary")
        btn_pick.clicked.connect(self._pick_custom_color)
        color_row.addWidget(btn_pick)
        layout_style.addLayout(color_row)

        # Couleur de fond de la Dynamic Island
        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel("Fond de l'Island :"))
        bg_row.addStretch()

        bg_presets = [
            ("#08080a", "OLED Noir Pur"),
            ("#16161e", "Gris Sidéral"),
            ("#0a1128", "Bleu Minuit"),
            ("#140924", "Violet Cosmique"),
            ("#1a090d", "Bordeaux Sombre"),
            ("#061a14", "Émeraude Sombre")
        ]
        for hex_code, name in bg_presets:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setProperty("class", "accent-btn")
            btn.setToolTip(name)
            btn.setStyleSheet(f"background-color: {hex_code}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.3);")
            btn.clicked.connect(lambda checked, c=hex_code: self._set_island_bg_color(c))
            bg_row.addWidget(btn)

        btn_bg_pick = QPushButton("Fond libre...")
        btn_bg_pick.setProperty("class", "secondary")
        btn_bg_pick.clicked.connect(self._pick_custom_island_bg_color)
        bg_row.addWidget(btn_bg_pick)
        layout_style.addLayout(bg_row)

        # Boutons de test d'états
        test_row = QHBoxLayout()
        test_row.setSpacing(4)
        states = [
            ("Repos", "idle"),
            ("Écoute", "listening"),
            ("Réflexion", "thinking"),
            ("Parole", "speaking"),
            ("Action", "action"),
        ]
        for label, st in states:
            b = QPushButton(label)
            b.setProperty("class", "secondary")
            b.clicked.connect(lambda checked, s=st: self.state_trigger_requested.emit(s))
            test_row.addWidget(b)
        layout_style.addLayout(test_row)

        content_layout.addWidget(card_style)

        # CARTE 4 : Raccourci Global Push-to-Talk (Windows + Alt)
        card_ptt = QFrame()
        card_ptt.setProperty("class", "card")
        layout_ptt = QVBoxLayout(card_ptt)
        layout_ptt.setSpacing(10)

        lbl_ptt = QLabel("Raccourci Clavier Global (Push-to-Talk)")
        lbl_ptt.setProperty("class", "section")
        layout_ptt.addWidget(lbl_ptt)

        # Touches matérielles détectées
        row_keys = QHBoxLayout()
        row_keys.addWidget(QLabel("Touches d'activation :"))
        row_keys.addStretch()
        
        badge_win = QLabel(" Win ")
        badge_win.setStyleSheet("background: #0284c7; color: #fff; font-weight: bold; border-radius: 4px; padding: 3px 8px; font-size: 11px;")
        badge_plus = QLabel("+")
        badge_plus.setStyleSheet("color: #94a3b8; font-weight: bold;")
        badge_alt = QLabel(" Alt ")
        badge_alt.setStyleSheet("background: #0284c7; color: #fff; font-weight: bold; border-radius: 4px; padding: 3px 8px; font-size: 11px;")
        
        row_keys.addWidget(badge_win)
        row_keys.addWidget(badge_plus)
        row_keys.addWidget(badge_alt)
        layout_ptt.addLayout(row_keys)

        # Mode Push-to-Talk
        row_ptt_mode = QHBoxLayout()
        row_ptt_mode.addWidget(QLabel("Comportement :"))
        row_ptt_mode.addStretch()
        self.combo_ptt = QComboBox()
        self.combo_ptt.blockSignals(True)
        self.combo_ptt.addItems([
            "Hybride (Tap court = Bascule, Maintien = Parler)",
            "Maintien enfonce (Push-to-Talk pur)",
            "Bascule on/off (Toggle)"
        ])
        mode_map = {"hybrid": 0, "hold": 1, "toggle": 2}
        self.combo_ptt.setCurrentIndex(mode_map.get(self.settings.get("ptt_mode", "hybrid"), 0))
        self.combo_ptt.blockSignals(False)
        self.combo_ptt.currentIndexChanged.connect(self._on_ptt_mode_changed)
        row_ptt_mode.addWidget(self.combo_ptt)
        layout_ptt.addLayout(row_ptt_mode)

        # Moteur Speech-to-Text (STT)
        row_stt = QHBoxLayout()
        row_stt.addWidget(QLabel("Reconnaissance Vocale (STT) :"))
        row_stt.addStretch()
        self.combo_stt = QComboBox()
        self.combo_stt.blockSignals(True)
        self.combo_stt.addItem("✨ Antigravity DeepMind (Connect-RPC Officiel)", "antigravity")
        self.combo_stt.addItem("☁️ Google Cloud Speech (Reconnaissance en ligne)", "google")
        self.combo_stt.addItem("💻 Windows Dictation Local (System.Speech)", "offline")

        cur_stt = self.settings.get("stt_provider", "antigravity")
        idx_stt = self.combo_stt.findData(cur_stt)
        if idx_stt >= 0:
            self.combo_stt.setCurrentIndex(idx_stt)
        self.combo_stt.blockSignals(False)
        self.combo_stt.currentIndexChanged.connect(self._on_stt_provider_changed)
        row_stt.addWidget(self.combo_stt)
        layout_ptt.addLayout(row_stt)

        content_layout.addWidget(card_ptt)

        # CARTE 5 : Intelligence Artificielle & Synthèse Vocale
        card_ai = QFrame()
        card_ai.setProperty("class", "card")
        layout_ai = QVBoxLayout(card_ai)
        layout_ai.setSpacing(10)

        lbl_ai = QLabel("Intelligence Artificielle & Voix")
        lbl_ai.setProperty("class", "section")
        layout_ai.addWidget(lbl_ai)

        # Fournisseur LLM (Agnes AI vs Google Gemini vs NVIDIA NIM vs Antigravity ACP)
        row_llm = QHBoxLayout()
        row_llm.addWidget(QLabel("Fournisseur IA (LLM Provider) :"))
        row_llm.addStretch()
        self.combo_llm = QComboBox()
        self.combo_llm.blockSignals(True)
        self.combo_llm.addItem("✨ Agnes AI 3.0 Flash (~0.8s - Par défaut & Vision)", "agnes")
        self.combo_llm.addItem("💎 Google DeepMind Gemini 2.5 Flash (<0.9s Direct)", "gemini")
        self.combo_llm.addItem("⚡ NVIDIA NIM (5 Modèles Rapides)", "nim")
        self.combo_llm.addItem("🧠 Antigravity CLI / AGY ACP (Local)", "agy")

        current_p = self.settings.get("llm_provider", "agnes")
        idx_llm = self.combo_llm.findData(current_p)
        if idx_llm >= 0:
            self.combo_llm.setCurrentIndex(idx_llm)
        self.combo_llm.blockSignals(False)
        self.combo_llm.currentIndexChanged.connect(self._on_llm_provider_changed)
        row_llm.addWidget(self.combo_llm)
        layout_ai.addLayout(row_llm)

        # Modèle NVIDIA NIM (5 modèles rapides & intelligents benchmarkés)
        row_nim_model = QHBoxLayout()
        row_nim_model.addWidget(QLabel("Modèle NVIDIA NIM :"))
        row_nim_model.addStretch()
        self.combo_nim_model = QComboBox()
        self.combo_nim_model.blockSignals(True)
        self.combo_nim_model.addItem("⚡ Nemotron 3.5 Bolt (0.35s - Vitesse Éclair)", "nvidia/nemotron-3.5-bolt-e4b")
        self.combo_nim_model.addItem("⚡ Poolside Laguna XS 2.1 (0.40s - Équilibré)", "poolside/laguna-xs-2.1")
        self.combo_nim_model.addItem("🧠 Google Gemma 4 31B (1.0s - Haute Précision)", "google/gemma-4-31b-it")
        self.combo_nim_model.addItem("🧩 Nemotron Nano Omni 30B (1.5s - Raisonnement)", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
        self.combo_nim_model.addItem("🔬 Nemotron 3.5 Super-VL 120B (2.0s - Multimodal)", "nvidia/nemotron-3.5-super-vl-120b-a12b")

        cur_model = self.settings.get("nim_model", "nvidia/nemotron-3.5-bolt-e4b")
        idx_m = self.combo_nim_model.findData(cur_model)
        if idx_m >= 0:
            self.combo_nim_model.setCurrentIndex(idx_m)
        self.combo_nim_model.blockSignals(False)
        self.combo_nim_model.currentIndexChanged.connect(self._on_nim_model_changed)
        row_nim_model.addWidget(self.combo_nim_model)
        layout_ai.addLayout(row_nim_model)

        # Modèle Antigravity AGY ACP
        row_agy_model = QHBoxLayout()
        row_agy_model.addWidget(QLabel("Modèle Antigravity AGY :"))
        row_agy_model.addStretch()
        self.combo_agy_model = QComboBox()
        self.combo_agy_model.blockSignals(True)
        self.combo_agy_model.addItem("💎 Gemini 3.8 Flash (Recommandé - Ultra rapide)", "gemini-3.8-flash")
        self.combo_agy_model.addItem("🧠 Claude Sonnet 4.6 (Thinking)", "claude-sonnet-4-6")
        self.combo_agy_model.addItem("👑 Claude Opus 4.6 (Thinking)", "claude-opus-4-6-thinking")
        self.combo_agy_model.addItem("⚡ GPT-OSS 120B (Medium)", "gpt-oss-120b-medium")

        cur_agy_m = self.settings.get("agy_model", "gemini-3.8-flash")
        idx_am = self.combo_agy_model.findData(cur_agy_m)
        if idx_am >= 0:
            self.combo_agy_model.setCurrentIndex(idx_am)
        self.combo_agy_model.blockSignals(False)
        self.combo_agy_model.currentIndexChanged.connect(self._on_agy_model_changed)
        row_agy_model.addWidget(self.combo_agy_model)
        layout_ai.addLayout(row_agy_model)

        # Niveau de réflexion AGY (Thought Level)
        row_agy_thought = QHBoxLayout()
        row_agy_thought.addWidget(QLabel("Réflexion AGY (Thought Level) :"))
        row_agy_thought.addStretch()
        self.combo_agy_thought = QComboBox()
        self.combo_agy_thought.blockSignals(True)
        self.combo_agy_thought.addItem("⚡ Rapide (Low - Idéal pour Island)", "low")
        self.combo_agy_thought.addItem("⚖️ Équilibré (Medium)", "medium")
        self.combo_agy_thought.addItem("🧠 Poussé (High - Réflexion complète)", "high")

        cur_th = self.settings.get("agy_thought_level", "low")
        idx_th = self.combo_agy_thought.findData(cur_th)
        if idx_th >= 0:
            self.combo_agy_thought.setCurrentIndex(idx_th)
        self.combo_agy_thought.blockSignals(False)
        self.combo_agy_thought.currentIndexChanged.connect(self._on_agy_thought_changed)
        row_agy_thought.addWidget(self.combo_agy_thought)
        layout_ai.addLayout(row_agy_thought)

        # Modèle Vision & Analyse d'écran
        row_vision = QHBoxLayout()
        row_vision.addWidget(QLabel("Vision & Analyse Écran :"))
        row_vision.addStretch()
        self.combo_vision = QComboBox()
        self.combo_vision.blockSignals(True)
        self.combo_vision.addItem("⚡ Agnes AI 3.0 Flash Vision (~1.0s - Recommandé)", "agnes")
        self.combo_vision.addItem("💎 Google DeepMind Gemini 2.5 Flash Vision (<0.9s)", "gemini_vl")
        self.combo_vision.addItem("🧠 Antigravity AGY ACP Vision (Local ~7s)", "agy_vl")
        self.combo_vision.addItem("🔬 NVIDIA Nemotron Super-VL 120B (~4.9s - NIM Multimodal)", "nim_vl")
        self.combo_vision.addItem("🔍 WinRT OCR Local (<0.15s - Texte seul)", "ocr")

        cur_vis = self.settings.get("vision_provider", "agnes")
        idx_vis = self.combo_vision.findData(cur_vis)
        if idx_vis >= 0:
            self.combo_vision.setCurrentIndex(idx_vis)
        self.combo_vision.blockSignals(False)
        self.combo_vision.currentIndexChanged.connect(self._on_vision_provider_changed)
        row_vision.addWidget(self.combo_vision)
        layout_ai.addLayout(row_vision)

        # Clé API Google Gemini (optionnelle pour Gemini Direct)
        row_gemini_key = QHBoxLayout()
        row_gemini_key.addWidget(QLabel("Clé Google Gemini (Direct) :"))
        self.txt_gemini_key = QLineEdit()
        self.txt_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_gemini_key.setPlaceholderText("AIzaSy... (laisser vide si non utilisé)")
        self.txt_gemini_key.setText(self.settings.get("gemini_api_key", ""))
        self.txt_gemini_key.textChanged.connect(self._on_gemini_key_changed)
        row_gemini_key.addWidget(self.txt_gemini_key)
        layout_ai.addLayout(row_gemini_key)

        # Synthèse vocale activée
        row_voice = QHBoxLayout()
        row_voice.addWidget(QLabel("Activer la parole (Edge-TTS naturel) :"))
        row_voice.addStretch()
        self.check_voice = QCheckBox()
        self.check_voice.blockSignals(True)
        self.check_voice.setChecked(self.settings.get("voice_enabled", True))
        self.check_voice.blockSignals(False)
        self.check_voice.toggled.connect(self._on_voice_toggled)
        row_voice.addWidget(self.check_voice)
        layout_ai.addLayout(row_voice)

        # Choix de la voix
        row_vname = QHBoxLayout()
        row_vname.addWidget(QLabel("Voix française :"))
        row_vname.addStretch()
        self.combo_voice = QComboBox()
        self.combo_voice.blockSignals(True)
        self.combo_voice.addItem("Vivienne (Ultra-Naturel & Rapide - Femme)", "fr-FR-VivienneMultilingualNeural")
        self.combo_voice.addItem("Remy (Ultra-Naturel - Homme)", "fr-FR-RemyMultilingualNeural")
        self.combo_voice.addItem("Henri (Expressif - Homme)", "fr-FR-HenriNeural")
        self.combo_voice.addItem("Denise (Expressif - Femme)", "fr-FR-DeniseNeural")
        self.combo_voice.addItem("Eloise (Douce - Femme)", "fr-FR-EloiseNeural")

        cur_v = self.settings.get("voice_name", "fr-FR-VivienneMultilingualNeural")
        idx_v = self.combo_voice.findData(cur_v)
        if idx_v >= 0:
            self.combo_voice.setCurrentIndex(idx_v)
        self.combo_voice.blockSignals(False)
        self.combo_voice.currentIndexChanged.connect(self._on_voice_name_changed)
        row_vname.addWidget(self.combo_voice)
        layout_ai.addLayout(row_vname)

        # Vitesse d'élocution
        row_vrate = QHBoxLayout()
        row_vrate.addWidget(QLabel("Débit / Vitesse :"))
        row_vrate.addStretch()
        self.combo_rate = QComboBox()
        self.combo_rate.blockSignals(True)
        self.combo_rate.addItem("Naturel & Posé (+10%)", "+10%")
        self.combo_rate.addItem("Standard (+0%)", "+0%")
        self.combo_rate.addItem("Rapide (+20%)", "+20%")
        self.combo_rate.addItem("Très dynamique (+30%)", "+30%")

        cur_r = self.settings.get("voice_rate", "+10%")
        idx_r = self.combo_rate.findData(cur_r)
        if idx_r >= 0:
            self.combo_rate.setCurrentIndex(idx_r)
        self.combo_rate.blockSignals(False)
        self.combo_rate.currentIndexChanged.connect(self._on_voice_rate_changed)
        row_vrate.addWidget(self.combo_rate)
        layout_ai.addLayout(row_vrate)

        # Bouton tester la voix
        btn_test_v = QPushButton("Écouter un exemple de voix")
        btn_test_v.setProperty("class", "secondary")
        btn_test_v.clicked.connect(self._test_voice)
        layout_ai.addWidget(btn_test_v)

        # Mémoire conversationnelle persistante DeepTalk
        row_deeptalk = QHBoxLayout()
        row_deeptalk.addWidget(QLabel("Mémoire persistante DeepTalk :"))
        row_deeptalk.addStretch()
        self.btn_clear_deeptalk = QPushButton("Effacer la mémoire")
        self.btn_clear_deeptalk.setProperty("class", "secondary")
        self.btn_clear_deeptalk.setStyleSheet("color: #ef4444; border-color: #ef4444; padding: 4px 10px; font-weight: bold;")
        self.btn_clear_deeptalk.clicked.connect(self._on_clear_deeptalk_clicked)
        row_deeptalk.addWidget(self.btn_clear_deeptalk)
        layout_ai.addLayout(row_deeptalk)

        content_layout.addWidget(card_ai)

        # CARTE 6 : Confidentialité & Présentations en Ligne (Google Meet / Teams / Zoom)
        card_privacy = QFrame()
        card_privacy.setProperty("class", "card")
        layout_privacy = QVBoxLayout(card_privacy)
        layout_privacy.setSpacing(10)

        lbl_privacy = QLabel("Confidentialité & Présentations en Ligne")
        lbl_privacy.setProperty("class", "section")
        layout_privacy.addWidget(lbl_privacy)

        desc_privacy = QLabel("Protège vos réunions en ligne : l'Island reste visible pour vous sur votre écran, mais devient 100% invisible pour vos interlocuteurs lors d'un partage d'écran (Google Meet, Microsoft Teams, Zoom, OBS).")
        desc_privacy.setWordWrap(True)
        desc_privacy.setStyleSheet("font-size: 11px; color: #94a3b8; line-height: 1.4;")
        layout_privacy.addWidget(desc_privacy)

        row_stealth = QHBoxLayout()
        row_stealth.addWidget(QLabel("Mode Furtif (Invisible en visioconférence / Meet) :"))
        row_stealth.addStretch()
        self.check_stealth = QCheckBox()
        self.check_stealth.blockSignals(True)
        self.check_stealth.setChecked(bool(self.settings.get("hide_on_screen_share", True)))
        self.check_stealth.blockSignals(False)
        self.check_stealth.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1e293b;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #38bdf8;
            }
        """)
        self.check_stealth.toggled.connect(self._on_stealth_toggled)
        row_stealth.addWidget(self.check_stealth)
        layout_privacy.addLayout(row_stealth)

        # Mode Meet (Assistant de Cours Automatique)
        row_meet = QHBoxLayout()
        row_meet.addWidget(QLabel("Mode Meet (Écouteur de cours automatique) :"))
        row_meet.addStretch()
        self.check_meet_mode = QCheckBox()
        self.check_meet_mode.blockSignals(True)
        self.check_meet_mode.setChecked(bool(self.settings.get("meet_mode_enabled", False)))
        self.check_meet_mode.blockSignals(False)
        self.check_meet_mode.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1e293b;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #38bdf8;
            }
        """)
        self.check_meet_mode.toggled.connect(self._on_meet_mode_toggled)
        row_meet.addWidget(self.check_meet_mode)
        layout_privacy.addLayout(row_meet)

        # Canal audio Meet (Loopback vs Hybride)
        row_meet_src = QHBoxLayout()
        row_meet_src.addWidget(QLabel("Canal d'écoute Meet :"))
        row_meet_src.addStretch()
        self.combo_meet_src = QComboBox()
        self.combo_meet_src.addItem("Haut-parleurs seuls (WASAPI Loopback - 100% Prof)", "loopback")
        self.combo_meet_src.addItem("Hybride (Haut-parleurs + Microphone)", "hybrid")
        curr_src = self.settings.get("meet_audio_source", "loopback")
        self.combo_meet_src.setCurrentIndex(1 if curr_src == "hybrid" else 0)
        self.combo_meet_src.currentIndexChanged.connect(self._on_meet_source_changed)
        row_meet_src.addWidget(self.combo_meet_src)
        layout_privacy.addLayout(row_meet_src)

        content_layout.addWidget(card_privacy)

        # CARTE 7 : Système & Démarrage Automatique
        card_sys = QFrame()
        card_sys.setProperty("class", "card")
        layout_sys = QVBoxLayout(card_sys)
        layout_sys.setSpacing(10)

        lbl_sys = QLabel("Système & Démarrage")
        lbl_sys.setProperty("class", "section")
        layout_sys.addWidget(lbl_sys)

        row_boot = QHBoxLayout()
        row_boot.addWidget(QLabel("Lancer au démarrage de Windows :"))
        row_boot.addStretch()
        self.check_autostart = QCheckBox()
        self.check_autostart.blockSignals(True)
        self.check_autostart.setChecked(is_autostart_enabled())
        self.check_autostart.blockSignals(False)
        self.check_autostart.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1e293b;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #38bdf8;
            }
        """)
        self.check_autostart.toggled.connect(self._on_autostart_toggled)
        row_boot.addWidget(self.check_autostart)
        layout_sys.addLayout(row_boot)

        content_layout.addWidget(card_sys)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        # Bouton Afficher / Masquer (Fixe en bas)
        self.toggle_btn = QPushButton("Masquer l'encoche" if self.settings.get("island_visible") else "Afficher l'encoche")
        self.toggle_btn.setProperty("class", "primary")
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        main_layout.addWidget(self.toggle_btn)

        # Pied de page (Fixe en bas)
        footer_layout = QHBoxLayout()
        footer_lbl = QLabel("Antigravity Island • 0 px gap header")
        footer_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        footer_layout.addWidget(footer_lbl)
        footer_layout.addStretch()

        quit_btn = QPushButton("Quitter")
        quit_btn.setStyleSheet("background: transparent; color: #ef4444; border: none; font-size: 12px;")
        quit_btn.clicked.connect(lambda: QApplication.quit())
        footer_layout.addWidget(quit_btn)
        main_layout.addLayout(footer_layout)

    def showEvent(self, event):
        """Applique l'invisibilité en capture d'écran si activée."""
        super().showEvent(event)
        try:
            import ctypes
            hwnd = int(self.winId())
            affinity = 0x00000011 if self.settings.get("hide_on_screen_share", True) else 0x00000000
            ctypes.windll.user32.SetWindowDisplayAffinity(ctypes.c_void_p(hwnd), ctypes.c_uint32(affinity))
        except Exception:
            pass

    def closeEvent(self, event):
        """Assure la sauvegarde automatique persistante lors de la fermeture de la fenêtre."""
        save_settings(self.settings)
        super().closeEvent(event)

    def _flash_saved(self):
        """Notification visuelle discrète de sauvegarde réussie."""
        if hasattr(self, "saved_badge"):
            self.saved_badge.setText("✓ Sauvegardé")
            self.saved_badge.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: 600;")
            QTimer.singleShot(1800, lambda: hasattr(self, "saved_badge") and self.saved_badge.setText("✓ Paramètres synchronisés") or self.saved_badge.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 500;"))

    def _on_style_changed(self, idx: int):
        style = "iphonex" if idx == 1 else "island"
        self.settings["style_mode"] = style
        if style == "iphonex":
            # L'encoche iPhone X s'ancre naturellement au bord supérieur (Y=0)
            self.combo_mode.blockSignals(True)
            self.combo_mode.setCurrentIndex(0)
            self.combo_mode.blockSignals(False)
            self.settings["position_mode"] = "notch"
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_mode_changed(self, idx: int):
        mode = "floating" if idx == 1 else "notch"
        self.settings["position_mode"] = mode
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_align_changed(self, idx: int):
        align_map = {0: "center", 1: "left", 2: "right"}
        self.settings["alignment"] = align_map.get(idx, "center")
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_width_changed(self, val: int):
        self.lbl_w_val.setText(f"{val} px")
        self.settings["idle_width"] = val
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_height_changed(self, val: int):
        self.lbl_h_val.setText(f"{val} px")
        self.settings["idle_height"] = val
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _set_accent_color(self, hex_color: str):
        self.settings["accent_color"] = hex_color
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _pick_custom_color(self):
        col = QColorDialog.getColor(QColor(self.settings.get("accent_color", "#38bdf8")), self, "Choisir une couleur")
        if col.isValid():
            self._set_accent_color(col.name())

    def _set_island_bg_color(self, hex_color: str):
        self.settings["island_bg_color"] = hex_color
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _pick_custom_island_bg_color(self):
        col = QColorDialog.getColor(QColor(self.settings.get("island_bg_color", "#08080a")), self, "Choisir la couleur de fond de l'Island")
        if col.isValid():
            self._set_island_bg_color(col.name())

    def _on_ptt_mode_changed(self, idx: int):
        modes = ["hybrid", "hold", "toggle"]
        self.settings["ptt_mode"] = modes[idx] if idx < len(modes) else "hybrid"
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_stt_provider_changed(self, idx: int):
        prov = self.combo_stt.currentData()
        self.settings["stt_provider"] = prov
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_screen_changed(self, idx: int):
        self.settings["screen_index"] = idx
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_llm_provider_changed(self, idx: int):
        p = self.combo_llm.currentData()
        self.settings["llm_provider"] = p
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_nim_model_changed(self, idx: int):
        m = self.combo_nim_model.currentData()
        self.settings["nim_model"] = m
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_agy_model_changed(self, idx: int):
        m = self.combo_agy_model.currentData()
        self.settings["agy_model"] = m
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()
        try:
            from island.agy_daemon import AgyDaemon
            AgyDaemon.get_instance().apply_config(model=m)
        except Exception:
            pass

    def _on_agy_thought_changed(self, idx: int):
        th = self.combo_agy_thought.currentData()
        self.settings["agy_thought_level"] = th
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()
        try:
            from island.agy_daemon import AgyDaemon
            AgyDaemon.get_instance().apply_config(thought_level=th)
        except Exception:
            pass

    def _on_vision_provider_changed(self, idx: int):
        v = self.combo_vision.currentData()
        self.settings["vision_provider"] = v
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_gemini_key_changed(self, text: str):
        self.settings["gemini_api_key"] = text.strip()
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_voice_toggled(self, checked: bool):
        self.settings["voice_enabled"] = checked
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_voice_name_changed(self, idx: int):
        v = self.combo_voice.currentData()
        self.settings["voice_name"] = v
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _on_voice_rate_changed(self, idx: int):
        r = self.combo_rate.currentData()
        self.settings["voice_rate"] = r
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self._flash_saved()

    def _test_voice(self):
        if self.island:
            v_name = self.settings.get("voice_name", "fr-FR-VivienneMultilingualNeural")
            v_rate = self.settings.get("voice_rate", "+20%")
            if hasattr(self.island, "voice_engine"):
                self.island.voice_engine.set_voice(v_name)
                self.island.voice_engine.set_rate(v_rate)
                self.island.set_state("speaking", {"text": "Bonjour ! La synthèse vocale est rapide, naturelle et fluide."})
                self.island.voice_engine.speak(
                    "Bonjour ! La synthèse vocale est rapide, naturelle et fluide.",
                    callback_on_finish=lambda: self.island.set_state("idle")
                )

    def _on_clear_deeptalk_clicked(self):
        try:
            from island.deeptalk import DeepTalk
            DeepTalk.get_instance().clear()
            self.btn_clear_deeptalk.setText("Mémoire effacée !")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.btn_clear_deeptalk.setText("Effacer la mémoire"))
        except Exception as e:
            print("[Settings] Erreur reset DeepTalk :", e)

    def _on_stealth_toggled(self, checked: bool):
        self.settings["hide_on_screen_share"] = bool(checked)
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        try:
            import ctypes
            hwnd = int(self.winId())
            affinity = 0x00000011 if checked else 0x00000000
            ctypes.windll.user32.SetWindowDisplayAffinity(ctypes.c_void_p(hwnd), ctypes.c_uint32(affinity))
        except Exception:
            pass
        self._flash_saved()

    def _on_meet_source_changed(self, index: int):
        src = self.combo_meet_src.currentData() or "loopback"
        self.settings["meet_audio_source"] = src
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        if getattr(self, "island_window", None):
            self.island_window.apply_settings(self.settings)
        self._flash_saved()

    def _on_meet_mode_toggled(self, checked: bool):
        self.settings["meet_mode_enabled"] = bool(checked)
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        if getattr(self, "island_window", None):
            self.island_window.set_meet_mode(bool(checked))
        self._flash_saved()

    def _on_autostart_toggled(self, checked: bool):
        set_autostart(checked)
        self.settings["autostart"] = checked
        save_settings(self.settings)
        self._flash_saved()

    def _on_toggle_clicked(self):
        new_val = not self.settings.get("island_visible", True)
        self.settings["island_visible"] = new_val
        save_settings(self.settings)
        self.toggle_btn.setText("Masquer l'encoche" if new_val else "Afficher l'encoche")
        self.toggle_island_requested.emit(new_val)
        self._flash_saved()
