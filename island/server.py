import asyncio
import json
import threading
import websockets
from island.config import Config

class IslandWebSocketServer:
    """
    Serveur WebSocket local exécuté en arrière-plan.
    Permet à Antigravity de piloter l'encoche par simple envoi de messages JSON.
    """

    def __init__(self, window_instance, host: str = Config.WS_HOST, port: int = Config.WS_PORT):
        self.window = window_instance
        self.host = host
        self.port = port
        self.thread = None
        self.loop = None
        self.server = None

    def start(self):
        """Démarre le serveur dans un thread dédié."""
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print(f"[IslandWebSocketServer] Serveur demarre sur ws://{self.host}:{self.port}")

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        async def handler(websocket):
            remote_ip = websocket.remote_address
            print(f"[IslandWebSocketServer] Client connecte : {remote_ip}")
            try:
                async for raw_msg in websocket:
                    try:
                        data = json.loads(raw_msg)
                        action = data.get("action", "set_state")

                        # Capture d'écran instantanée (Vision HeyClicky)
                        if action == "capture_screen":
                            from island.vision import capture_screen
                            shot_res = capture_screen(monitor_index=data.get("monitor", 1))
                            await websocket.send(json.dumps(shot_res, ensure_ascii=False))
                            continue
                        elif action == "get_screens":
                            from island.vision import get_screens_info
                            info = get_screens_info()
                            await websocket.send(json.dumps(info, ensure_ascii=False))
                            continue

                        # Transmission thread-safe à l'interface PyQt6
                        self.window.state_change_requested.emit(action, data)
                        
                        # Accusé de réception
                        response = {
                            "status": "success",
                            "action": action,
                            "current_state": data.get("state", self.window.current_state)
                        }
                        await websocket.send(json.dumps(response))
                    except json.JSONDecodeError:
                        await websocket.send(json.dumps({"status": "error", "message": "JSON invalide"}))
            except websockets.exceptions.ConnectionClosed:
                print(f"[IslandWebSocketServer] Client deconnecte : {remote_ip}")

        async def main():
            async with websockets.serve(handler, self.host, self.port):
                await asyncio.Future()

        try:
            self.loop.run_until_complete(main())
        except Exception as e:
            print(f"[IslandWebSocketServer] Erreur : {e}")
