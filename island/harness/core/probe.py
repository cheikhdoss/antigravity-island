# Copyright 2026 Google LLC - Harness² Architecture
# Desktop Probing Subsystem

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional, Dict, Any

user32 = ctypes.windll.user32

@dataclass
class ProbeResult:
    target: str
    exists: bool
    details: Dict[str, Any]
    confidence: float = 1.0

class DesktopProber:
    """
    Système de sondes (Probes) ultra-rapides sans effet de bord pour Harness².
    Permet à l'agent de vérifier l'état du système AVANT d'exécuter une action.
    """

    @staticmethod
    def probe_window(target_name: str) -> ProbeResult:
        """Sonde l'existence et l'état d'une fenêtre applicative en <0.001s."""
        from island.window_manager import AppWindowManager
        manager = AppWindowManager()
        wins = manager.get_all_open_windows()

        target_lower = target_name.lower().strip()
        matched = None
        for w in wins:
            if target_lower in w["app_name"].lower() or target_lower in w["title"].lower():
                matched = w
                break

        if matched:
            return ProbeResult(
                target=target_name,
                exists=True,
                details=matched,
                confidence=0.95
            )
        return ProbeResult(target=target_name, exists=False, details={}, confidence=0.1)

    @staticmethod
    def probe_file(query: str) -> ProbeResult:
        """Sonde l'existence d'un fichier via le RAG en <0.002s."""
        from island.rag.client import RAGClient
        rag = RAGClient.get_instance()
        results = rag.search_files(query, limit=1)
        if results:
            best = results[0]
            return ProbeResult(
                target=query,
                exists=True,
                details=best,
                confidence=0.9
            )
        return ProbeResult(target=query, exists=False, details={}, confidence=0.0)
