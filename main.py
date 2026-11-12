import sys
import os
import time

# Redirection sécurisée des flux standards vers %APPDATA%\AntigravityIsland pour PyInstaller --windowed
appdata_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AntigravityIsland")
os.makedirs(appdata_dir, exist_ok=True)
log_file_path = os.path.join(appdata_dir, "antigravity_island.log")
trace_log_path = os.path.join(appdata_dir, "startup_trace.log")

def trace(msg):
    try:
        with open(trace_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

try:
    log_file = open(log_file_path, "a", encoding="utf-8", buffering=1)
    class FlushWriter:
        def __init__(self, f): self.f = f
        def write(self, s):
            self.f.write(s)
            self.f.flush()
        def flush(self): self.f.flush()
    sys.stdout = FlushWriter(log_file)
    sys.stderr = FlushWriter(log_file)
except Exception:
    class NullWriter:
        def write(self, s): pass
        def flush(self): pass
    sys.stdout = NullWriter()
    sys.stderr = NullWriter()

def global_excepthook(exc_type, exc_value, exc_tb):
    import traceback
    err_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("[UNCAUGHT EXCEPTION]", err_str)
    try:
        crash_log = os.path.join(appdata_dir, "crash_dump.log")
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write(f"\n=== CRASH CAPTURED ===\n{err_str}\n")
    except Exception:
        pass

sys.excepthook = global_excepthook

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt6.QtCore import Qt

from island.window import IslandWindow
from island.settings_window import SettingsWindow, load_settings, save_settings
from island.server import IslandWebSocketServer
from island.hotkey import PushToTalkEngine
from island.agy_daemon import AgyDaemon

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

import subprocess

def kill_other_instances():
    """Ferme toute ancienne instance résiduelle pour garantir un démarrage propre et immédiat."""
    try:
        import psutil
        cur_pid = os.getpid()
        parent_pid = os.getppid()
        for proc in psutil.process_iter(['pid', 'name', 'ppid']):
            pid = proc.info['pid']
            ppid = proc.info.get('ppid')
            if pid != cur_pid and pid != parent_pid and ppid != cur_pid and proc.info['name'] and 'antigravityisland' in proc.info['name'].lower():
                try:
                    proc.kill()
                except Exception:
                    pass
    except Exception:
        pass

def main():
    trace("Step: main starting")
    kill_other_instances()
    trace("Step: kill_other_instances done")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Antigravity Island")
    app.setQuitOnLastWindowClosed(False)
    trace("Step: QApplication created")

    # 1. Charger les réglages
    user_settings = load_settings()
    trace("Step: load_settings done")

    # 2. Fenêtre de l'encoche (Overlay Dynamic Island)
    island = IslandWindow()
    island.apply_settings(user_settings)
    if user_settings.get("island_visible", True):
        island.show()
    trace("Step: IslandWindow created and shown")

    # 3. Fenêtre de contrôle & Réglages (Centre de contrôle accessible via clic droit ou System Tray)
    control_center = SettingsWindow(island_window=island)
    island.settings_window = control_center
    trace("Step: SettingsWindow created")

    # Sauvegarde garantie en cas d'arrêt de l'application
    app.aboutToQuit.connect(lambda: save_settings(control_center.settings))
    app.aboutToQuit.connect(lambda: AgyDaemon.get_instance().stop())

    # Pré-chauffage asynchrone du démon LLM officiel (même architecture qu'Open Design)
    import threading
    threading.Thread(target=lambda: AgyDaemon.get_instance(), daemon=True).start()
    trace("Step: AgyDaemon prewarm thread launched")

    # Lier les signaux du centre de contrôle à l'île
    control_center.settings_changed.connect(island.apply_settings)
    control_center.state_trigger_requested.connect(lambda st: island.set_state(st))
    control_center.toggle_island_requested.connect(lambda vis: island.show() if vis else island.hide())

    # 4. Serveur WebSocket d'arrière-plan pour pilotage Antigravity
    server = IslandWebSocketServer(island)
    server.start()
    trace("Step: IslandWebSocketServer started")

    # 5. Moteur Push-to-Talk global (Raccourci Windows + Alt)
    ptt_engine = PushToTalkEngine(window_instance=island, mode=user_settings.get("ptt_mode", "hybrid"))
    island.ptt_engine = ptt_engine
    ptt_engine.start()
    control_center.settings_changed.connect(lambda s: ptt_engine.set_mode(s.get("ptt_mode", "hybrid")))
    trace("Step: PushToTalkEngine started")

    # 6. Icône dans la zone de notification Windows (System Tray)
    tray = QSystemTrayIcon(create_tray_icon(), app)
    tray_menu = QMenu()

    action_settings = tray_menu.addAction("Ouvrir le Centre de contrôle")
    action_settings.triggered.connect(control_center.show)
    action_settings.triggered.connect(control_center.raise_)
    action_settings.triggered.connect(control_center.activateWindow)

    tray_menu.addSeparator()

    action_stealth = tray_menu.addAction("Mode Furtif (Invisible en Meet / Présentation)")
    action_stealth.setCheckable(True)
    action_stealth.setChecked(bool(user_settings.get("hide_on_screen_share", True)))

    def toggle_stealth_from_tray(checked):
        control_center.settings["hide_on_screen_share"] = checked
        save_settings(control_center.settings)
        control_center.settings_changed.emit(control_center.settings)
        if hasattr(control_center, "check_stealth"):
            control_center.check_stealth.blockSignals(True)
            control_center.check_stealth.setChecked(checked)
            control_center.check_stealth.blockSignals(False)

    action_stealth.triggered.connect(toggle_stealth_from_tray)
    control_center.settings_changed.connect(lambda s: action_stealth.setChecked(bool(s.get("hide_on_screen_share", True))))

    action_toggle = tray_menu.addAction("Basculer l'encoche")
    action_toggle.triggered.connect(lambda: island.hide() if island.isVisible() else island.show())

    tray_menu.addSeparator()

    action_quit = tray_menu.addAction("Quitter Antigravity Island")
    action_quit.triggered.connect(app.quit)

    tray.setContextMenu(tray_menu)
    tray.setToolTip("Antigravity Island - En ligne")
    tray.show()
    trace("Step: SystemTrayIcon shown")

    # 7. Heartbeat diagnostic pour détecter le point exact de toute interruption
    from PyQt6.QtCore import QTimer
    hb_timer = QTimer(island)
    hb_count = [0]
    def on_hb():
        hb_count[0] += 1
        trace(f"Heartbeat: {hb_count[0]}s (State: {island.current_state})")
    hb_timer.timeout.connect(on_hb)
    hb_timer.start(1000)

    print("============================================================")
    print("[Antigravity Island] Application et Centre de controle lances.")
    print("Fenetre de configuration ouverte pour personnaliser l'application.")
    print("Icone active dans la zone de notification (System Tray).")
    print("============================================================")
    trace("Step: Entering app.exec()")

    sys.exit(app.exec())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        with open(r"C:\Users\pro\.gemini\antigravity\scratch\island_debug.log", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
