from dataclasses import dataclass
from PyQt6.QtGui import QColor

@dataclass
class IslandStateConfig:
    width: int
    height: int
    radius: int
    title: str

class Config:
    # Paramètres de placement
    TOP_MARGIN = 0         # 0 pour être collé au bord supérieur comme une vraie encoche
    SHADOW_BLUR = 24       # Rayon de l'ombre
    SHADOW_OFFSET_Y = 6    # Décalage vertical de l'ombre
    
    # Couleurs & Thème (Obsidian Apple Craft)
    COLOR_BG = QColor(10, 10, 14, 250)
    COLOR_BORDER = QColor(255, 255, 255, 30)
    COLOR_SHADOW = QColor(0, 0, 0, 160)
    
    COLOR_ACCENT_CYAN = QColor(56, 189, 248)    # #38bdf8
    COLOR_ACCENT_GREEN = QColor(34, 197, 94)    # #22c55e
    COLOR_ACCENT_PURPLE = QColor(168, 85, 247)  # #a855f7
    COLOR_ACCENT_ORANGE = QColor(249, 115, 22)  # #f97316
    
    COLOR_TEXT_PRIMARY = QColor(250, 250, 252)
    COLOR_TEXT_SECONDARY = QColor(156, 163, 175)
    
    # Configurations des états
    STATES = {
        "idle": IslandStateConfig(
            width=110,
            height=30,
            radius=15,
            title=""
        ),
        "listening": IslandStateConfig(
            width=340,
            height=50,
            radius=25,
            title="À votre écoute..."
        ),
        "thinking": IslandStateConfig(
            width=280,
            height=46,
            radius=23,
            title="Analyse en cours..."
        ),
        "speaking": IslandStateConfig(
            width=480,
            height=90,
            radius=28,
            title="Réponse"
        ),
        "prompt_input": IslandStateConfig(
            width=480,
            height=52,
            radius=26,
            title="Saisie clavier"
        ),
        "action": IslandStateConfig(
            width=500,
            height=124,
            radius=30,
            title="Action de l'agent"
        ),
        "notification": IslandStateConfig(
            width=460,
            height=76,
            radius=26,
            title="Notification"
        ),
        "minimized_dock": IslandStateConfig(
            width=320,
            height=54,
            radius=24,
            title="Applications ouvertes"
        ),
        "control_hub": IslandStateConfig(
            width=700,
            height=280,
            radius=28,
            title="Hub d'actions & Contrôle"
        )
    }
    
    # Port WebSocket pour Antigravity
    WS_PORT = 8765
    WS_HOST = "127.0.0.1"
