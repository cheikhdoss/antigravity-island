import os
import sys
import json
import time
import queue
import threading
import subprocess
import re
from typing import Optional, Callable

AGY_PATH = r"C:\Users\pro\AppData\Local\agy\bin\agy.EXE"

class AgyDaemon:
    """
    Client persistant pour le démon agy CLI via le protocole Agent Client Protocol (ACP).
    Maintient une instance unique d'agy active en arrière-plan pendant toute la durée de vie
    de l'application (exactement comme le fait Open Design), éliminant ainsi toute latence
    de démarrage de processus et permettant des réponses streaming ultra-rapides.
    """

    _instance: Optional["AgyDaemon"] = None
    _singleton_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "AgyDaemon":
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self, workspace_cwd: Optional[str] = None):
        if workspace_cwd:
            self.workspace_cwd = workspace_cwd
        else:
            self.workspace_cwd = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
        os.makedirs(self.workspace_cwd, exist_ok=True)
        self.process: Optional[subprocess.Popen] = None
        self.session_id: Optional[str] = None
        self.is_ready = False
        self._running = False
        self._lock = threading.Lock()
        self._req_id = 0
        self._pending_requests = {}
        self._reader_thread: Optional[threading.Thread] = None

        self._start_daemon()

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _start_daemon(self):
        if not os.path.exists(AGY_PATH):
            print(f"[AgyDaemon] Exécutable introuvable : {AGY_PATH}")
            return

        try:
            cmd = [AGY_PATH, "acp", "--dangerously-skip-permissions"]
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=0x08000000  # CREATE_NO_WINDOW : aucun clignotement de terminal
            )
            self._running = True

            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()

            # 1. Initialize
            init_id = self._next_id()
            res_init = self._send_request_sync("initialize", {"protocolVersion": 1, "capabilities": {}}, req_id=init_id, timeout=10.0)
            if not res_init:
                print("[AgyDaemon] Échec de l'initialisation ACP")
                return

            # 2. Session New
            new_id = self._next_id()
            res_new = self._send_request_sync("session/new", {"cwd": self.workspace_cwd}, req_id=new_id, timeout=10.0)
            if not res_new or "sessionId" not in res_new:
                print(f"[AgyDaemon] Échec de création de session : {res_new}")
                return

            self.session_id = res_new["sessionId"]
            print(f"[AgyDaemon] Session ACP active : {self.session_id}")

            # 3. Configuration du modèle rapide (gemini-3.8-flash) et pensée low pour latence minimale
            try:
                mod_id = self._next_id()
                self._send_request_sync("session/set_config_option", {"sessionId": self.session_id, "configId": "model", "value": "gemini-3.8-flash"}, req_id=mod_id, timeout=5.0)
            except Exception:
                pass

            try:
                cfg_id = self._next_id()
                self._send_request_sync("session/set_config_option", {"sessionId": self.session_id, "configId": "thought_level", "value": "low"}, req_id=cfg_id, timeout=5.0)
            except Exception:
                pass

            self.is_ready = True
            print("[AgyDaemon] Démon Antigravity ACP opérationnel et prêt !")

            # 4. Pré-chauffage asynchrone
            threading.Thread(target=self._prewarm, daemon=True).start()

        except Exception as e:
            print(f"[AgyDaemon] Erreur lors du démarrage du démon : {e}")
            self._running = False

    def _prewarm(self):
        """Pré-chauffe la session LLM pour éliminer tout temps d'attente à la première question de l'utilisateur."""
        try:
            time.sleep(1.0)
            print("[AgyDaemon] Pré-chauffage du modèle LLM en tâche de fond...")
            self.ask("Bonjour", timeout=25.0)
            print("[AgyDaemon] Modèle LLM pré-chauffé avec succès !")
        except Exception as e:
            print(f"[AgyDaemon] Note pré-chauffage : {e}")

    def _send_request_sync(self, method: str, params: dict, req_id: Optional[int] = None, timeout: float = 10.0) -> Optional[dict]:
        if not self.process or not self.process.stdin:
            return None

        rid = req_id if req_id is not None else self._next_id()
        evt = threading.Event()
        container = {"result": None, "error": None, "event": evt}
        self._pending_requests[rid] = container

        payload = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": params
        }

        try:
            line = json.dumps(payload, ensure_ascii=False) + "\n"
            self.process.stdin.write(line)
            self.process.stdin.flush()
        except Exception as e:
            print(f"[AgyDaemon] Erreur écriture stdin : {e}")
            self._pending_requests.pop(rid, None)
            return None

        if evt.wait(timeout):
            self._pending_requests.pop(rid, None)
            if container["error"]:
                print(f"[AgyDaemon] Erreur RPC ({method}) : {container['error']}")
                return None
            return container["result"]

        self._pending_requests.pop(rid, None)
        print(f"[AgyDaemon] Timeout RPC ({method}) après {timeout}s")
        return None

    def _read_loop(self):
        while self._running and self.process and self.process.stdout:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue

                obj = json.loads(line)
                # 1. Traitement des réponses RPC avec id
                if "id" in obj:
                    rid = obj["id"]
                    if rid in self._pending_requests:
                        req = self._pending_requests[rid]
                        if "error" in obj and obj["error"]:
                            req["error"] = obj["error"]
                        else:
                            req["result"] = obj.get("result", {})
                        req["event"].set()

                # 2. Traitement des notifications de streaming (session/update)
                elif obj.get("method") == "session/update":
                    params = obj.get("params", {})
                    update = params.get("update", {})
                    session_update = update.get("sessionUpdate")

                    if session_update == "agent_message_chunk":
                        content = update.get("content", {})
                        text = content.get("text", "")
                        if text and hasattr(self, "_active_chunk_callback") and self._active_chunk_callback:
                            try:
                                self._active_chunk_callback(text)
                            except Exception:
                                pass

            except Exception as e:
                if self._running:
                    print(f"[AgyDaemon] Erreur parsing stdout : {e}")

        print("[AgyDaemon] Boucle de lecture stdout terminée.")

    def ask(self, prompt: str, on_chunk: Optional[Callable[[str], None]] = None, timeout: float = 30.0) -> str:
        """
        Envoie un prompt au modèle LLM persistant et renvoie la réponse complète ultra-rapide.
        """
        if not prompt or not prompt.strip():
            return ""

        with self._lock:
            if not self.is_ready or not self.session_id or not self.process or self.process.poll() is not None:
                print("[AgyDaemon] Démon inactif, tentative de redémarrage...")
                self._start_daemon()

            if not self.is_ready or not self.session_id:
                return ""

            chunks = []

            def _handle_chunk(txt: str):
                chunks.append(txt)
                if on_chunk:
                    try:
                        on_chunk(txt)
                    except Exception:
                        pass

            self._active_chunk_callback = _handle_chunk

            req_id = self._next_id()
            evt = threading.Event()
            container = {"result": None, "error": None, "event": evt}
            self._pending_requests[req_id] = container

            system_context = (
                "Consigne: Tu es l'assistant de l'encoche Dynamic Island sur Windows. "
                "Réponds IMMÉDIATEMENT en 1 SEULE phrase concise et directe en français, sans réflexion ni préambule. "
                "Ne mets aucun emoji ni astérisques markdown.\n\n"
                f"Question : {prompt.strip()}"
            )

            prompt_payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "session/prompt",
                "params": {
                    "sessionId": self.session_id,
                    "prompt": [{"type": "text", "text": system_context}]
                }
            }

            try:
                line = json.dumps(prompt_payload, ensure_ascii=False) + "\n"
                self.process.stdin.write(line)
                self.process.stdin.flush()
            except Exception as e:
                print(f"[AgyDaemon] Erreur d'écriture du prompt : {e}")
                self._pending_requests.pop(req_id, None)
                self._active_chunk_callback = None
                return ""

            completed = evt.wait(timeout)
            self._pending_requests.pop(req_id, None)
            self._active_chunk_callback = None

            if not completed:
                print(f"[AgyDaemon] Timeout sur session/prompt après {timeout}s")
                if chunks:
                    return self._clean_text("".join(chunks))
                return ""

            raw_text = "".join(chunks).strip()
            clean_text = self._clean_text(raw_text)
            return clean_text

    def _clean_text(self, text: str) -> str:
        """Nettoie le texte des astérisques markdown et préfixes parasites pour une diction vocale parfaite."""
        if not text:
            return ""
        # Enlever les astérisques markdown (* ou **)
        t = re.sub(r'\*+', '', text)
        # Enlever les balises ou code fences
        t = re.sub(r'```.*?```', '', t, flags=re.DOTALL)
        t = re.sub(r'`', '', t)
        # Enlever les préfixes de type "Antigravity :" ou "Réponse :"
        t = re.sub(r'^(Antigravity\s*:|Réponse\s*:|Ta réponse\s*:)\s*', '', t, flags=re.IGNORECASE)
        # Remplacer les sauts de lignes multiples par un espace
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def stop(self):
        """Arrête proprement le processus démon agy."""
        self._running = False
        self.is_ready = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
        print("[AgyDaemon] Démon arrêté proprement.")
