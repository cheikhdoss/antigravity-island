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
                        elif action == "find_elements":
                            from island.ocr import find_screen_elements
                            query = data.get("query", "")
                            image_path = data.get("image_path", None)
                            loop = asyncio.get_running_loop()
                            elements = await loop.run_in_executor(None, find_screen_elements, query, image_path)
                            await websocket.send(json.dumps({
                                "status": "success",
                                "query": query,
                                "count": len(elements),
                                "elements": elements
                            }, ensure_ascii=False))
                            continue
                        elif action == "click":
                            from island.automation import click
                            x = data.get("x")
                            y = data.get("y")
                            button = data.get("button", "left")
                            double = data.get("double", False)
                            smooth = data.get("smooth", True)
                            loop = asyncio.get_running_loop()
                            await loop.run_in_executor(None, click, x, y, button, double, smooth)
                            await websocket.send(json.dumps({
                                "status": "success",
                                "action": "click",
                                "x": x,
                                "y": y,
                                "button": button
                            }, ensure_ascii=False))
                            continue
                        elif action == "move_cursor":
                            from island.automation import move_cursor_smooth
                            x = data.get("x")
                            y = data.get("y")
                            duration = float(data.get("duration", 0.35))
                            loop = asyncio.get_running_loop()
                            await loop.run_in_executor(None, move_cursor_smooth, x, y, duration)
                            await websocket.send(json.dumps({
                                "status": "success",
                                "action": "move_cursor",
                                "x": x,
                                "y": y
                            }, ensure_ascii=False))
                            continue
                        elif action == "type":
                            from island.automation import type_text
                            text = data.get("text", "")
                            delay = float(data.get("delay", 0.015))
                            loop = asyncio.get_running_loop()
                            await loop.run_in_executor(None, type_text, text, delay)
                            await websocket.send(json.dumps({
                                "status": "success",
                                "action": "type",
                                "length": len(text)
                            }, ensure_ascii=False))
                            continue
                        elif action == "press_key":
                            from island.automation import press_key
                            key_combo = data.get("key", "")
                            loop = asyncio.get_running_loop()
                            await loop.run_in_executor(None, press_key, key_combo)
                            await websocket.send(json.dumps({
                                "status": "success",
                                "action": "press_key",
                                "key": key_combo
                            }, ensure_ascii=False))
                            continue
                        elif action == "scroll":
                            from island.automation import scroll
                            amount = int(data.get("amount", -3))
                            loop = asyncio.get_running_loop()
                            await loop.run_in_executor(None, scroll, amount)
                            await websocket.send(json.dumps({
                                "status": "success",
                                "action": "scroll",
                                "amount": amount
                            }, ensure_ascii=False))
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
