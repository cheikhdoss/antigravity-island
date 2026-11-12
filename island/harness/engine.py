# Copyright 2026 Google LLC - Harness² Architecture
# Island Harness² Central Engine

import os
import re
import time
from typing import Optional, Tuple, Dict, Any, List
from island.harness.core.library import ExperienceLibrary
from island.harness.core.probe import DesktopProber, ProbeResult

class HarnessEngine:
    """
    Moteur d'orchestration récursive Harness² pour Antigravity Island.
    Applique la boucle Propose-Probe-Compose et la persistance d'expériences
    pour un comportement d'agent autonome fiable, rapide (<0.5s) et sans oubli.
    """
    _instance: Optional["HarnessEngine"] = None

    @classmethod
    def get_instance(cls) -> "HarnessEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.library = ExperienceLibrary()
        self.prober = DesktopProber()

    def get_context_lessons(self, query: str) -> str:
        """Injecte les leçons Harness² apprises pour guider le raisonnement du LLM."""
        lessons = self.library.find_relevant_lessons(query, limit=2)
        if not lessons:
            return ""

        context_str = "\n[EXPÉRIENCES PASSÉES HARNESS² / RÈGLES APPRISES] :\n"
        for l in lessons:
            context_str += f"- Déclencheur: {l['cue']} -> Leçon: {l['lesson']}\n"
        return context_str

    def execute_recursive(self, query: str) -> Optional[Tuple[bool, str]]:
        """
        Exécute la boucle récursive Propose-Probe-Compose sur la requête utilisateur.
        Retourne (succès, message) si une action est composée et exécutée, sinon None.
        """
        q = query.lower().strip()
        t0 = time.time()

        # 1. Détection de requêtes sur les fichiers / documents (RAG Probe)
        file_match = re.search(r'(?:ouvre|cherche|trouve|montre|où est|ou est|lance)\s+(?:le\s+)?(?:fichier|document|projet|rapport|cours|tp)?\s*([a-zA-Z0-9_\-\.\s]{2,40})', q)
        if file_match and any(kw in q for kw in ["fichier", "document", "projet", "tp", "pdf", "note", "code"]):
            target_file = file_match.group(1).strip()
            # PROBE : Vérifier dans l'index RAG
            probe = self.prober.probe_file(target_file)
            if probe.exists:
                file_info = probe.details
                file_path = file_info["path"]
                # COMPOSE : Ouvrir le fichier ou l'afficher
                try:
                    os.startfile(file_path)
                    msg = f"Fichier trouvé et ouvert : {file_info['name']}"
                    # REFLECT : Mémoriser le succès
                    self.library.record_experience(
                        cue=f"ouvrir {target_file}",
                        lesson=f"Fichier localisé dans {file_info['dir']}",
                        evidence=f"Statut ouvert en {time.time() - t0:.3f}s",
                        domain="files",
                        task_id=f"open_file_{int(time.time())}"
                    )
                    return True, msg
                except Exception as e:
                    return False, f"Fichier localisé ({file_info['name']}) mais erreur d'ouverture : {e}"

        # 2. Détection de requêtes sur les applications (Window Probe)
        app_match = re.search(r'(?:ouvre|bascule sur|va sur|affiche|mets au premier plan)\s+([a-zA-Z0-9_\-\s]{2,25})', q)
        if app_match and not any(kw in q for kw in ["fichier", "document", "onglet", "ligne"]):
            app_target = app_match.group(1).strip()
            # PROBE : Vérifier si l'application est déjà ouverte
            probe = self.prober.probe_window(app_target)
            if probe.exists:
                win = probe.details
                from island.window_manager import AppWindowManager
                AppWindowManager().activate_window(win["hwnd"])
                msg = f"{win['app_name']} est passé au premier plan."
                # REFLECT
                self.library.record_experience(
                    cue=f"bascule {app_target}",
                    lesson=f"Application active sous HWND {win['hwnd']}",
                    evidence=f"Bascule en {time.time() - t0:.3f}s",
                    domain="windows",
                    task_id=f"focus_app_{int(time.time())}"
                )
                return True, msg

        return None
