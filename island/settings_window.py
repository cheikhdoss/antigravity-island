import sys
import json
import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QSlider, QComboBox, QSystemTrayIcon, QMenu, QColorDialog, QScrollArea
)
from PyQt6.QtGui import QIcon, QColor, QFont, QPixmap, QPainter, QBrush

from island.config import Config

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
        "style_mode": "island",      # "island" (pilule) ou "iphonex" (encoche iPhone X)
        "position_mode": "notch",   # "notch" (collé au bord) ou "floating"
        "alignment": "center",       # "center", "left", "right"
        "idle_width": 110,           # Largeur au repos
        "idle_height": 30,           # Hauteur au repos
        "island_visible": True,
        "ptt_mode": "hybrid",        # "hybrid", "hold", "toggle"
    }
    settings_path = get_settings_file_path()
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_settings.update(data)
                print(f"[Settings] Paramètres chargés depuis {settings_path}")
        except Exception as e:
            print("Erreur lecture settings:", e)
    else:
        save_settings(default_settings)
    return default_settings

def save_settings(settings):
    try:
        settings_path = get_settings_file_path()
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        print(f"[Settings] Paramètres enregistrés dans {settings_path}")
    except Exception as e:
        print("Erreur sauvegarde settings:", e)

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
        self.setFixedSize(520, 730)
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
                font-weight: 500;
                min-width: 220px;
            }
            QComboBox:hover {
                border-color: #38bdf8;
                background-color: #243247;
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
                color: #f8fafc;
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
        self.combo_style.addItems(["Dynamic Island (Pilule moderne)", "Encoche iPhone X (Notch avec cornes)"])
        if self.settings.get("style_mode") == "iphonex":
            self.combo_style.setCurrentIndex(1)
        self.combo_style.currentIndexChanged.connect(self._on_style_changed)
        row_style.addWidget(self.combo_style)
        layout_disp.addLayout(row_style)

        # Accrochage au bord (Notch collé vs Flottant)
        row_pos = QHBoxLayout()
        row_pos.addWidget(QLabel("Fixation :"))
        row_pos.addStretch()
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Collé au plus près du bord (Notch Y=0)", "Flottant (Capsule détachée)"])
        if self.settings.get("position_mode") == "floating":
            self.combo_mode.setCurrentIndex(1)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        row_pos.addWidget(self.combo_mode)
        layout_disp.addLayout(row_pos)

        # Alignement Horizontal
        row_align = QHBoxLayout()
        row_align.addWidget(QLabel("Alignement :"))
        row_align.addStretch()
        self.combo_align = QComboBox()
        self.combo_align.addItems(["Centre (Recommandé)", "Gauche", "Droite"])
        cur_align = self.settings.get("alignment", "center")
        if cur_align == "left":
            self.combo_align.setCurrentIndex(1)
        elif cur_align == "right":
            self.combo_align.setCurrentIndex(2)
        self.combo_align.currentIndexChanged.connect(self._on_align_changed)
        row_align.addWidget(self.combo_align)
        layout_disp.addLayout(row_align)

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
        self.slider_w.setValue(int(self.settings.get("idle_width", 110)))
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
        self.slider_h.setValue(int(self.settings.get("idle_height", 30)))
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
        self.combo_ptt.addItems([
            "Hybride (Tap court = Bascule, Maintien = Parler)",
            "Maintien enfonce (Push-to-Talk pur)",
            "Bascule on/off (Toggle)"
        ])
        mode_map = {"hybrid": 0, "hold": 1, "toggle": 2}
        self.combo_ptt.setCurrentIndex(mode_map.get(self.settings.get("ptt_mode", "hybrid"), 0))
        self.combo_ptt.currentIndexChanged.connect(self._on_ptt_mode_changed)
        row_ptt_mode.addWidget(self.combo_ptt)
        layout_ptt.addLayout(row_ptt_mode)

        content_layout.addWidget(card_ptt)

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

    def _on_style_changed(self, idx: int):
        style = "iphonex" if idx == 1 else "island"
        self.settings["style_mode"] = style
        if style == "iphonex":
            # L'encoche iPhone X s'ancre naturellement au bord de l'écran (Y=0)
            self.combo_mode.setCurrentIndex(0)
            self.settings["position_mode"] = "notch"
            # Donner une largeur d'encoche iPhone X harmonieuse si elle était trop petite
            if self.settings.get("idle_width", 110) < 140:
                self.slider_w.setValue(160)
                self.settings["idle_width"] = 160
                self.lbl_w_val.setText("160 px")
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)

    def _on_mode_changed(self, idx: int):
        mode = "floating" if idx == 1 else "notch"
        self.settings["position_mode"] = mode
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)

    def _on_align_changed(self, idx: int):
        align_map = {0: "center", 1: "left", 2: "right"}
        self.settings["alignment"] = align_map.get(idx, "center")
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)

    def _on_width_changed(self, val: int):
        self.lbl_w_val.setText(f"{val} px")
        self.settings["idle_width"] = val
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)

    def _on_height_changed(self, val: int):
        self.lbl_h_val.setText(f"{val} px")
        self.settings["idle_height"] = val
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)

    def _set_accent_color(self, hex_color: str):
        self.settings["accent_color"] = hex_color
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)

    def _pick_custom_color(self):
        col = QColorDialog.getColor(QColor(self.settings.get("accent_color", "#38bdf8")), self, "Choisir une couleur")
        if col.isValid():
            self._set_accent_color(col.name())

    def _on_ptt_mode_changed(self, idx: int):
        modes = ["hybrid", "hold", "toggle"]
        self.settings["ptt_mode"] = modes[idx] if idx < len(modes) else "hybrid"
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)

    def _on_toggle_clicked(self):
        new_val = not self.settings.get("island_visible", True)
        self.settings["island_visible"] = new_val
        save_settings(self.settings)
        self.toggle_btn.setText("Masquer l'encoche" if new_val else "Afficher l'encoche")
        self.toggle_island_requested.emit(new_val)
