# Copyright 2026 Antigravity - Live Session Lifecycle & Contextual Junctions Engine
# island/session_manager.py

import os
import sys
import json
import time
import uuid
import re
import threading
from datetime import datetime
from typing import List, Dict, Optional, Any

class IslandSessionManager:
    """
    Gestionnaire du cycle de vie des sessions d'Antigravity Island :
    - Démarre à chaque lancement / redémarrage de l'Island jusqu'à son arrêt ou redémarrage.
    - Consigne l'intégralité des messages, actions, analyses visuelles et contextes de la session active.
    - Moteur de Jonctions Contextuelles : permet à Island de relier intelligemment les questions
      actuelles aux éléments abordés plus tôt dans la session (ex: "le deuxième", "le projet de tout à l'heure",
      "pourquoi cette action", "ce que tu as dit au début").
    - Archivage automatique à la fermeture propre ou à la détection d'une session précédente non fermée.
    """
    _instance: Optional["IslandSessionManager"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "IslandSessionManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self.appdata_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AntigravityIsland")
        self.sessions_dir = os.path.join(self.appdata_dir, "sessions")
        self.history_dir = os.path.join(self.sessions_dir, "history")
        self.active_session_file = os.path.join(self.sessions_dir, "active_session.json")

        os.makedirs(self.history_dir, exist_ok=True)

        self.session_id: str = ""
        self.start_time: float = 0.0
        self.start_iso: str = ""
        self.events: List[Dict[str, Any]] = []
        self.entities_registry: Dict[str, Any] = {}
        self.is_active: bool = False
        self._turn_counter: int = 0

    def start_session(self) -> str:
        """Initialise une nouvelle session active au démarrage de l'Island."""
        with self._lock:
            # 1. Vérifier si une session antérieure n'a pas été fermée proprement
            self._archive_previous_session_if_needed()

            self.start_time = time.time()
            now = datetime.now()
            self.start_iso = now.strftime("%Y-%m-%d %H:%M:%S")
            self.session_id = f"island_sess_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            self.events = []
            self.entities_registry = {
                "projects_mentioned": [],
                "topics": [],
                "last_active_window": "",
                "actions_performed": []
            }
            self.is_active = True
            self._turn_counter = 0

            self._save_active_session()
            print(f"[IslandSession] Nouvelle session active démarrée : {self.session_id} à {self.start_iso}")
            return self.session_id

    def _archive_previous_session_if_needed(self):
        """Si une session précédente existe encore dans active_session.json, on l'archive."""
        try:
            if os.path.exists(self.active_session_file):
                with open(self.active_session_file, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                old_id = old_data.get("session_id", f"recovered_{int(time.time())}")
                archive_path = os.path.join(self.history_dir, f"{old_id}_closed.json")
                old_data["status"] = "archived_on_new_boot"
                old_data["closed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(archive_path, "w", encoding="utf-8") as f:
                    json.dump(old_data, f, ensure_ascii=False, indent=2)
                try:
                    os.remove(self.active_session_file)
                except Exception:
                    pass
                print(f"[IslandSession] Ancienne session {old_id} archivée dans history.")
        except Exception as e:
            print(f"[IslandSession] Note archivage session précédente : {e}")

    def _save_active_session(self):
        """Sauvegarde atomique de la session vivante."""
        if not self.is_active:
            return
        snapshot = {
            "session_id": self.session_id,
            "status": "active",
            "start_time": self.start_time,
            "start_iso": self.start_iso,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": round(time.time() - self.start_time, 1),
            "turn_count": self._turn_counter,
            "entities": self.entities_registry,
            "events": self.events
        }
        tmp_path = f"{self.active_session_file}.tmp_{os.getpid()}"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.active_session_file)
        except Exception as e:
            print(f"[IslandSession] Erreur écriture session active : {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def record_turn(self, user_query: str, response: str, event_type: str = "chat", action: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        Enregistre un événement / échange complet dans la session vivante.
        Permet d'établir des ponts contextuels (jonctions) avec les requêtes ultérieures.
        """
        if not self.is_active:
            self.start_session()

        u_clean = (user_query or "").strip()
        r_clean = (response or "").strip()

        # Filtrer les simples alertes techniques de micro inaudible pour ne pas polluer l'historique
        if any(kw in r_clean.lower() for kw in ["microphone inaudible", "parlez un peu plus près"]):
            return

        with self._lock:
            self._turn_counter += 1
            now = datetime.now()
            time_str = now.strftime("%H:%M:%S")

            # Extraction rapide de mots-clés et sujets pour faciliter les jonctions
            extracted_keywords = self._extract_keywords(f"{u_clean} {r_clean}")

            # Détection d'entités projet clés
            low = f"{u_clean} {r_clean}".lower()
            for proj in ["senstory", "samapdf", "samatop", "second brain", "antigravity island", "dokploy", "supabase", "cloudflare"]:
                if proj in low and proj not in self.entities_registry["projects_mentioned"]:
                    self.entities_registry["projects_mentioned"].append(proj)

            event = {
                "turn_id": self._turn_counter,
                "timestamp": time.time(),
                "time_str": time_str,
                "type": event_type,
                "user_query": u_clean,
                "response": r_clean,
                "action": action,
                "keywords": extracted_keywords,
                "metadata": metadata or {}
            }

            self.events.append(event)
            self._save_active_session()
            print(f"[IslandSession] Échange #{self._turn_counter} consigné [{event_type}] ({len(self.events)} au total dans la session).")

    def _extract_keywords(self, text: str) -> List[str]:
        """Extrait les tokens et entités significatives pour la jonction associative."""
        stop_words = {
            "le", "la", "les", "un", "une", "des", "du", "de", "d", "l", "ce", "cet", "cette", "ces",
            "et", "ou", "mais", "donc", "or", "ni", "car", "pour", "dans", "sur", "avec", "sans",
            "est", "sont", "ete", "a", "ont", "qui", "que", "quoi", "dont", "ou", "quand", "comment",
            "je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "mon", "ton", "son", "notre",
            "votre", "leur", "moi", "toi", "lui", "eux", "en", "y", "ne", "pas", "plus", "tout", "tous"
        }
        words = re.findall(r'[a-zA-Z0-9àâäéèêëîïôöùûüç\-_]{3,}', text.lower())
        meaningful = [w for w in words if w not in stop_words and not w.isdigit()]
        # Garder les termes uniques dans l'ordre d'apparition
        seen = set()
        unique = []
        for w in meaningful:
            if w not in seen:
                seen.add(w)
                unique.append(w)
        return unique[:15]

    def find_junctions(self, current_query: str) -> List[Dict[str, Any]]:
        """
        Détecte les connexions sémantiques et contextuelles (jonctions)
        entre la nouvelle requête et l'ensemble des échanges de la session active.
        """
        if not self.events:
            return []

        import unicodedata
        def strip_accents(s: str) -> str:
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()

        q_raw = current_query.lower().strip()
        q_clean = strip_accents(q_raw)
        matched_turns = []

        # 1. Raccourcis anaphoriques et ordinaux ("premier", "deuxième", "second", "dernier", etc.)
        ordinal_keywords = [
            "premier", "premiere", "1er", "1ere",
            "deuxieme", "second", "seconde", "2eme",
            "troisieme", "3eme", "quatrieme", "4eme",
            "cinquieme", "5eme", "dernier", "derniere", "avant-dernier"
        ]
        has_ordinal_ref = any(ord_k in q_clean for ord_k in ordinal_keywords)

        # 2. Références temporelles ou de rappel
        temporal_keywords = [
            "tout a l'heure", "au debut", "au demarrage", "precedent", "d'avant",
            "de tout a l'heure", "tu disais", "tu as dit", "tu m'as dit",
            "dont tu parlais", "dont on parlait", "rappelle-moi", "tu te souviens",
            "on a dit quoi", "on disait", "le meme", "la meme", "celui-ci", "celle-ci", "celui-la"
        ]
        has_temporal_ref = any(t in q_clean for t in temporal_keywords)

        # 3. Mots-clés de la requête
        q_keywords = set(strip_accents(w) for w in self._extract_keywords(q_raw))

        for event in self.events:
            score = 0
            ev_resp_raw = event.get("response", "")
            ev_resp_clean = strip_accents(ev_resp_raw)
            ev_query_clean = strip_accents(event.get("user_query", ""))
            ev_keywords = set(strip_accents(w) for w in event.get("keywords", []))

            # Chevauchement de mots-clés
            overlap = q_keywords.intersection(ev_keywords)
            score += len(overlap) * 2

            # Bonus ordinal : si la requête cherche un élément ordinal ("le deuxième"),
            # et que cette réponse contenait une liste ordonnée ("1.", "2.", etc.)
            if has_ordinal_ref:
                has_list_pattern = any(p in ev_resp_clean for p in ["1.", "2.", "1 -", "2 -", "1)", "2)", "top 5", "top 10"])
                if has_list_pattern:
                    score += 10

            # Bonus temporel : si "au début", bonus aux premiers tours
            if "au debut" in q_clean or "au demarrage" in q_clean:
                if event["turn_id"] == 1:
                    score += 8
            elif "precedent" in q_clean or "d'avant" in q_clean:
                if event["turn_id"] == len(self.events):
                    score += 8

            # Bonus si mention du même projet
            for proj in self.entities_registry.get("projects_mentioned", []):
                p_clean = strip_accents(proj)
                if p_clean in q_clean and (p_clean in ev_query_clean or p_clean in ev_resp_clean):
                    score += 5

            # Si le score est positif, conserver la jonction
            if score > 0:
                matched_turns.append({
                    "event": event,
                    "score": score,
                    "overlap": list(overlap)
                })

        # Trier par score décroissant, puis par récence
        matched_turns.sort(key=lambda x: (x["score"], x["event"]["turn_id"]), reverse=True)
        return matched_turns[:4]

    def get_junction_prompt(self, current_query: str) -> str:
        """
        Construit le bloc de jonction contextuelle injecté dans le prompt de tous les LLMs.
        Fournit l'historique complet de la session active + les liens spécifiques détectés.
        """
        with self._lock:
            if not self.events:
                return ""

            elapsed_min = max(1, int((time.time() - self.start_time) / 60))
            lines = [
                "==================================================================",
                f"[MÉMOIRE DE LA SESSION ACTIVE D'ANTIGRAVITY ISLAND]",
                f"Session ID : {self.session_id} | Démarrée à : {self.start_iso} (il y a {elapsed_min} min)",
                f"Nombre total d'échanges dans cette session : {len(self.events)} tour(s)",
                "------------------------------------------------------------------"
            ]

            # Synthèse chronologique de la session (les 6 derniers événements pour vue globale)
            lines.append("Chronologie des échanges récents de cette session :")
            recent_events = self.events[-6:]
            for ev in recent_events:
                tid = ev["turn_id"]
                t_str = ev["time_str"]
                uq = ev["user_query"]
                # Tronquer la réponse à 160 caractères pour ne pas surcharger la fenêtre contextuelle
                resp_preview = ev["response"].replace("\n", " ").strip()
                if len(resp_preview) > 160:
                    resp_preview = resp_preview[:157] + "..."
                act_str = f" [Action bureau : {ev['action']}]" if ev.get("action") else ""
                lines.append(f"  • Tour #{tid} [{t_str}] : Utilisateur: « {uq} » => Island: « {resp_preview} »{act_str}")

            # Jonctions spécifiques trouvées
            junctions = self.find_junctions(current_query)
            if junctions:
                lines.append("------------------------------------------------------------------")
                lines.append(">>> JONCTIONS CONTEXTUELLES CLÉS DÉTECTÉES POUR CETTE QUESTION :")
                for j in junctions:
                    ev = j["event"]
                    lines.append(f"  * Référence au Tour #{ev['turn_id']} [{ev['time_str']}] (Pertinence: {j['score']}) :")
                    lines.append(f"    Demande initiale : « {ev['user_query']} »")
                    lines.append(f"    Contenu de la réponse Island : « {ev['response']} »")
                lines.append("CONSIGNE DE JONCTION : L'utilisateur se réfère aux éléments ci-dessus.")
                lines.append("Établis le lien immédiatement avec précision sans lui demander de répéter.")

            lines.append("==================================================================")
            return "\n".join(lines)

    def get_session_summary_answer(self) -> str:
        """Répond directement si l'utilisateur demande un résumé de ce qui a été fait dans la session."""
        with self._lock:
            if not self.events:
                return "Cette session vient de démarrer. Aucun échange ou action n'a encore été enregistré."

            elapsed_min = max(1, int((time.time() - self.start_time) / 60))
            count = len(self.events)
            lines = [f"Depuis le lancement de cette session ({self.start_iso}, soit environ {elapsed_min} min), nous avons eu {count} échange(s) :"]
            for ev in self.events:
                lines.append(f"- Tour {ev['turn_id']} ({ev['time_str']}) : {ev['user_query']}")
                if ev.get("action"):
                    lines.append(f"  ↳ Action exécutée : {ev['action']}")
            return "\n".join(lines)

    def close_session(self):
        """Ferme la session proprement à l'arrêt d'Antigravity Island et l'archive."""
        with self._lock:
            if not self.is_active:
                return

            self.is_active = False
            now = datetime.now()
            closed_iso = now.strftime("%Y-%m-%d %H:%M:%S")
            duration = round(time.time() - self.start_time, 1)

            final_data = {
                "session_id": self.session_id,
                "status": "closed",
                "start_time": self.start_time,
                "start_iso": self.start_iso,
                "closed_at": closed_iso,
                "duration_seconds": duration,
                "duration_minutes": round(duration / 60.0, 1),
                "total_turns": self._turn_counter,
                "entities": self.entities_registry,
                "events": self.events
            }

            archive_path = os.path.join(self.history_dir, f"{self.session_id}.json")
            try:
                with open(archive_path, "w", encoding="utf-8") as f:
                    json.dump(final_data, f, ensure_ascii=False, indent=2)
                if os.path.exists(self.active_session_file):
                    os.remove(self.active_session_file)
                print(f"[IslandSession] Session {self.session_id} clôturée avec succès ({self._turn_counter} tours, {round(duration/60.0, 1)} min).")
            except Exception as e:
                print(f"[IslandSession] Erreur lors de l'archivage final : {e}")
