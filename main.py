import sys
import os

# Redirection sécurisée des flux standards pour PyInstaller --windowed
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "antigravity_island.log")
try:
    log_file = open(log_file_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = log_file
    sys.stderr = log_file
except Exception:
    class NullWriter:
        def write(self, s): pass
        def flush(self): pass
    sys.stdout = NullWriter()
    sys.stderr = NullWriter()

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt6.QtCore import Qt

from island.window import IslandWindow
from island.settings_window import SettingsWindow, load_settings
from island.server import IslandWebSocketServer
from island.hotkey import PushToTalkEngine

def create_tray_icon():
    """Crée une icône pour la barre des tâches système Windows (System Tray)."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    
    # Fond sombre rond
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(10, 10, 14)))
    painter.drawEllipse(2, 2, 28, 28)
    
    # Point cyan Antigravity
    painter.setBrush(QBrush(QColor(56, 189, 248)))
    painter.drawEllipse(11, 11, 10, 10)
    painter.end()
    
    return QIcon(pixmap)

def try_notify_existing_instance() -> bool:
    """Si une instance tourne déjà, lui demande d'afficher son centre de contrôle et retourne True."""
    import socket, json
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    try:
        s.connect(("127.0.0.1", 8765))
        s.close()
        import websockets, asyncio
        async def notify():
            async with websockets.connect("ws://127.0.0.1:8765", open_timeout=0.8) as ws:
                await ws.send(json.dumps({"action": "show_control_center"}))
        try:
            asyncio.run(notify())
        except Exception:
            pass
        return True
    except Exception:
        s.close()
        return False

def main():
    if try_notify_existing_instance():
        print("[Antigravity Island] Instance existante notifiée et mise au premier plan.")
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Antigravity Island")
    app.setQuitOnLastWindowClosed(False)

    # 1. Charger les réglages
    user_settings = load_settings()

    # 2. Fenêtre de l'encoche (Overlay Dynamic Island)
    island = IslandWindow()
    island.apply_settings(user_settings)
    if user_settings.get("island_visible", True):
        island.show()

    # 3. Fenêtre de contrôle & Réglages (Centre de contrôle de l'application)
    control_center = SettingsWindow(island_window=island)
    island.settings_window = control_center
    control_center.show()

    # Sauvegarde garantie en cas d'arrêt de l'application
    app.aboutToQuit.connect(lambda: save_settings(control_center.settings))

    # Lier les signaux du centre de contrôle à l'île
    control_center.settings_changed.connect(island.apply_settings)
    control_center.state_trigger_requested.connect(lambda st: island.set_state(st))
    control_center.toggle_island_requested.connect(lambda vis: island.show() if vis else island.hide())

    # 4. Serveur WebSocket d'arrière-plan pour pilotage Antigravity
    server = IslandWebSocketServer(island)
    server.start()

    # 5. Moteur Push-to-Talk global (Raccourci Windows + Alt)
    ptt_engine = PushToTalkEngine(window_instance=island, mode=user_settings.get("ptt_mode", "hybrid"))
    ptt_engine.start()
    control_center.settings_changed.connect(lambda s: ptt_engine.set_mode(s.get("ptt_mode", "hybrid")))

    # 6. Icône dans la zone de notification Windows (System Tray)
    tray = QSystemTrayIcon(create_tray_icon(), app)
    tray_menu = QMenu()

    action_settings = tray_menu.addAction("Ouvrir le Centre de contrôle")
    action_settings.triggered.connect(control_center.show)
    action_settings.triggered.connect(control_center.raise_)
    action_settings.triggered.connect(control_center.activateWindow)

    tray_menu.addSeparator()

    action_toggle = tray_menu.addAction("Basculer l'encoche")
    action_toggle.triggered.connect(lambda: island.hide() if island.isVisible() else island.show())

    tray_menu.addSeparator()

    action_quit = tray_menu.addAction("Quitter Antigravity Island")
    action_quit.triggered.connect(app.quit)

    tray.setContextMenu(tray_menu)
    tray.setToolTip("Antigravity Island - En ligne")
    tray.show()

    print("============================================================")
    print("[Antigravity Island] Application et Centre de controle lances.")
    print("Fenetre de configuration ouverte pour personnaliser l'application.")
    print("Icone active dans la zone de notification (System Tray).")
    print("============================================================")

    sys.exit(app.exec())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        with open(r"C:\Users\pro\.gemini\antigravity\scratch\island_debug.log", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
