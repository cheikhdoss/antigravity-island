# Copyright 2026 Antigravity - DeepTalk Persistent Conversational Memory Engine
# island/deeptalk.py

import os
import json
import time
import re
import threading
from typing import List, Dict, Optional

class DeepTalk:
    """
    Moteur de mémoire conversationnelle persistante multi-tours pour Antigravity Island.
    - Conserve l'historique des échanges (User / Assistant) même après un redémarrage complet du PC.
    - Fenêtre glissante adaptative (10 derniers tours = 20 messages maximum).
    - Nettoyage automatique des balises internes (<think>, blocs JSON d'actions) pour une mémoire conversationnelle pure.
    - Réinitialisation instantanée sur commande vocale ("oublie la discussion") ou action UI.
    - Stockage atomique et asynchrone dans %APPDATA%\\AntigravityIsland\\deeptalk_memory.json.
    """
    _instance: Optional["DeepTalk"] = None

    @classmethod
    def get_instance(cls) -> "DeepTalk":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self._lock = threading.Lock()
        self.history: List[Dict[str, str]] = []

        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        self.storage_dir = os.path.join(appdata, "AntigravityIsland")
        self.storage_file = os.path.join(self.storage_dir, "deeptalk_memory.json")

        self._load()

    def _load(self):
        """Charge l'historique conversationnel depuis le disque au démarrage du PC."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # Valider la structure des messages
                        valid_msgs = [m for m in data if isinstance(m, dict) and "role" in m and "content" in m]
                        self.history = valid_msgs[-(self.max_turns * 2):]
                        turns = len(self.history) // 2
                        print(f"[DeepTalk] Mémoire persistante restaurée avec succès : {turns} tour(s) en mémoire.")
        except Exception as e:
            print("[DeepTalk] Erreur chargement mémoire :", e)
            self.history = []

    def _save_async(self):
        """Sauvegarde asynchrone sans bloquer le thread de réponse UI."""
        with self._lock:
            snapshot = list(self.history)

        def _writer():
            try:
                os.makedirs(self.storage_dir, exist_ok=True)
                tmp_file = self.storage_file + ".tmp"
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f, ensure_ascii=False, indent=2)
                if os.path.exists(self.storage_file):
                    os.replace(tmp_file, self.storage_file)
                else:
                    os.rename(tmp_file, self.storage_file)
            except Exception as e:
                print("[DeepTalk] Erreur écriture persistante :", e)

        threading.Thread(target=_writer, daemon=True).start()

    def record_turn(self, user_query: str, assistant_response: str):
        """Enregistre un tour de dialogue complet dans la mémoire persistante."""
        if not user_query or not assistant_response:
            return

        u_clean = user_query.strip()
        a_clean = assistant_response.strip()

        # Ne pas polluer la mémoire avec les messages système d'erreur micro
        if any(kw in a_clean.lower() for kw in ["microphone inaudible", "n'ai pas bien compris", "parlez un peu plus près"]):
            return

        # Nettoyage des balises internes <think> et extraction du message naturel
        a_clean = re.sub(r'<think>.*?</think>', '', a_clean, flags=re.DOTALL).strip()
        if "```json" in a_clean or a_clean.startswith("{"):
            match = re.search(r'"say"\s*:\s*"([^"]+)"', a_clean)
            if match:
                a_clean = match.group(1).strip()

        with self._lock:
            self.history.append({"role": "user", "content": u_clean})
            self.history.append({"role": "assistant", "content": a_clean})

            # Maintenir la fenêtre glissante aux N derniers tours
            if len(self.history) > (self.max_turns * 2):
                self.history = self.history[-(self.max_turns * 2):]

        self._save_async()

    def get_messages_for_llm(self, current_query: str, system_prompt: str) -> List[Dict[str, str]]:
        """
        Construit la liste multi-tours pour les API OpenAI / NVIDIA NIM / Agnes AI :
        [system, user_prev_1, assistant_prev_1, ..., current_user]
        """
        messages = [{"role": "system", "content": system_prompt}]
        with self._lock:
            for msg in self.history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": current_query})
        return messages

    def get_context_summary_text(self, limit_turns: int = 4) -> str:
        """
        Génère un résumé textuel des derniers tours pour les backends mono-invite (ex. ACP CLI).
        """
        with self._lock:
            if not self.history:
                return ""
            recent = self.history[-(limit_turns * 2):]
            lines = ["[HISTORIQUE CONVERSATIONNEL RÉCENT (DEEPTALK)] :"]
            for msg in recent:
                speaker = "Utilisateur" if msg["role"] == "user" else "Antigravity Island"
                lines.append(f"- {speaker} : {msg['content']}")
            return "\n".join(lines) + "\n\n"

    def clear(self):
        """Réinitialise totalement la mémoire conversationnelle active et sur disque."""
        with self._lock:
            self.history = []
        self._save_async()
        print("[DeepTalk] Mémoire conversationnelle DeepTalk réinitialisée à zéro.")

    def count_turns(self) -> int:
        with self._lock:
            return len(self.history) // 2

    def get_last_topic(self) -> Optional[str]:
        with self._lock:
            if self.history:
                for msg in reversed(self.history):
                    if msg["role"] == "user":
                        return msg["content"]
        return None
