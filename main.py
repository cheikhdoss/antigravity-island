import sys
from PyQt6.QtWidgets import QApplication
from island.window import IslandWindow
from island.server import IslandWebSocketServer

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Antigravity Island")
    app.setQuitOnLastWindowClosed(False)

    # 1. Instanciation de l'île
    window = IslandWindow()
    window.show()

    # 2. Démarrage du serveur de contrôle WebSocket
    server = IslandWebSocketServer(window)
    server.start()

    print("=" * 60)
    print("🏝️  Antigravity Island est active sur votre écran !")
    print("👉 Cliquez sur l'encoche pour cycler manuellement entre les états :")
    print("   [IDLE] -> [LISTENING] -> [THINKING] -> [SPEAKING] -> [ACTION]")
    print("👉 Clic droit : Retour immédiat à l'état IDLE")
    print("👉 Ou envoyez des commandes WebSocket sur ws://127.0.0.1:8765")
    print("=" * 60)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
