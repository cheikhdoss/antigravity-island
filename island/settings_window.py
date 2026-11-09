import sys
import json
import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QSlider, QComboBox, QSystemTrayIcon, QMenu, QColorDialog
)
from PyQt6.QtGui import QIcon, QColor, QFont, QPixmap, QPainter, QBrush

from island.config import Config

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "user_settings.json")

def load_settings():
    default_settings = {
        "accent_color": "#38bdf8",
        "position_mode": "top",  # "top" (collé) ou "floating" (flottant à 12px)
        "island_visible": True,
        "opacity": 250
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_settings.update(data)
        except Exception:
            pass
    return default_settings

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print("Erreur sauvegarde settings:", e)

class SettingsWindow(QWidget):
    """
    Panneau de contrôle & Paramètres pour Antigravity Island.
    Permet à l'utilisateur de configurer visuellement son application locale sans ligne de commande.
    """
    settings_changed = pyqtSignal(dict)
    state_trigger_requested = pyqtSignal(str)
    toggle_island_requested = pyqtSignal(bool)

    def __init__(self, island_window=None):
        super().__init__()
        self.island_window = island_window
        self.settings = load_settings()

        self.setWindowTitle("Antigravity Control Center")
        self.setFixedSize(480, 560)
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
                padding: 16px;
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
                font-size: 13px;
                font-weight: 600;
                color: #38bdf8;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QPushButton.primary {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: 600;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
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
                padding: 7px 12px;
            }
            QPushButton.secondary:hover {
                background-color: #334155;
                border-color: #475569;
            }
            QPushButton.accent-btn {
                border-radius: 15px;
                border: 2px solid transparent;
            }
            QPushButton.accent-btn:hover {
                border-color: #ffffff;
            }
        """)

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        # En-tête
        header_layout = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("Antigravity Island")
        title.setProperty("class", "title")
        subtitle = QLabel("Centre de contrôle & Paramètres locaux")
        subtitle.setProperty("class", "subtitle")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        # Statut Serveur
        status_badge = QLabel("  ● En ligne (8765)  ")
        status_badge.setStyleSheet("background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; font-size: 11px; font-weight: 600; padding: 4px 8px;")
        header_layout.addWidget(status_badge)
        main_layout.addLayout(header_layout)

        # Carte 1 : Contrôle de l'encoche
        card1 = QFrame()
        card1.setProperty("class", "card")
        card1_layout = QVBoxLayout(card1)
        card1_layout.setSpacing(12)

        lbl1 = QLabel("Affichage & État de l'Encoche")
        lbl1.setProperty("class", "section")
        card1_layout.addWidget(lbl1)

        # Bouton Toggle Visibilité
        toggle_layout = QHBoxLayout()
        self.toggle_btn = QPushButton("Masquer l'encoche" if self.settings.get("island_visible") else "Afficher l'encoche")
        self.toggle_btn.setProperty("class", "primary")
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        toggle_layout.addWidget(self.toggle_btn)
        card1_layout.addLayout(toggle_layout)

        # Tester les états en direct
        lbl_tests = QLabel("Tester les états de l'île en un clic :")
        lbl_tests.setStyleSheet("font-size: 12px; color: #94a3b8; margin-top: 4px;")
        card1_layout.addWidget(lbl_tests)

        btn_grid = QHBoxLayout()
        btn_grid.setSpacing(6)

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
            b.clicked.connect(lambda checked, s=st: self._trigger_state(s))
            btn_grid.addWidget(b)

        card1_layout.addLayout(btn_grid)
        main_layout.addWidget(card1)

        # Carte 2 : Personnalisation Visuelle
        card2 = QFrame()
        card2.setProperty("class", "card")
        card2_layout = QVBoxLayout(card2)
        card2_layout.setSpacing(12)

        lbl2 = QLabel("Personnalisation de la Couleur")
        lbl2.setProperty("class", "section")
        card2_layout.addWidget(lbl2)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Palette préférée :"))
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
            btn.setFixedSize(28, 28)
            btn.setProperty("class", "accent-btn")
            btn.setToolTip(name)
            btn.setStyleSheet(f"background-color: {hex_code}; border-radius: 14px;")
            btn.clicked.connect(lambda checked, c=hex_code: self._set_accent_color(c))
            color_row.addWidget(btn)

        # Bouton Sélecteur Libre
        custom_color_btn = QPushButton("Personnaliser...")
        custom_color_btn.setProperty("class", "secondary")
        custom_color_btn.clicked.connect(self._pick_custom_color)
        color_row.addWidget(custom_color_btn)

        card2_layout.addLayout(color_row)

        # Mode de position (Collé vs Flottant)
        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("Positionnement :"))
        pos_row.addStretch()
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(["Collée en haut (Notch)", "Flottante (Capsule)"])
        if self.settings.get("position_mode") == "floating":
            self.pos_combo.setCurrentIndex(1)
        self.pos_combo.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 5px 12px;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        self.pos_combo.currentIndexChanged.connect(self._on_pos_changed)
        pos_row.addWidget(self.pos_combo)
        card2_layout.addLayout(pos_row)

        main_layout.addWidget(card2)
        main_layout.addStretch()

        # Pied de page
        footer_layout = QHBoxLayout()
        footer_lbl = QLabel("Antigravity Island v0.1.0 • Prêt pour connexion MCP")
        footer_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        footer_layout.addWidget(footer_lbl)
        footer_layout.addStretch()

        quit_btn = QPushButton("Quitter l'application")
        quit_btn.setStyleSheet("background: transparent; color: #ef4444; border: none; font-size: 12px;")
        quit_btn.clicked.connect(self._quit_app)
        footer_layout.addWidget(quit_btn)

        main_layout.addLayout(footer_layout)

    def _on_toggle_clicked(self):
        new_val = not self.settings.get("island_visible", True)
        self.settings["island_visible"] = new_val
        save_settings(self.settings)
        self.toggle_btn.setText("Masquer l'encoche" if new_val else "Afficher l'encoche")
        self.toggle_island_requested.emit(new_val)

    def _trigger_state(self, state: str):
        self.state_trigger_requested.emit(state)

    def _set_accent_color(self, hex_color: str):
        self.settings["accent_color"] = hex_color
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)

    def _pick_custom_color(self):
        col = QColorDialog.getColor(QColor(self.settings.get("accent_color", "#38bdf8")), self, "Choisir une couleur d'accent")
        if col.isValid():
            self._set_accent_color(col.name())

    def _on_pos_changed(self, idx: int):
        mode = "floating" if idx == 1 else "top"
        self.settings["position_mode"] = mode
        save_settings(self.settings)
        self.settings_changed.emit(self.settings)

    def _quit_app(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
