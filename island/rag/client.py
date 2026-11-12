import os
import time
import subprocess
import urllib.request
import json
from typing import List, Dict, Optional, Tuple
from island.rag.indexer import LocalRAGIndexer

CHROMA_URL = "http://localhost:8000/api/v1"

class RAGClient:
    """
    Client RAG unifié pour Antigravity Island :
    - Accès immédiat (<0.005s) au moteur d'indexation mémoire local.
    - Passerelle vers le conteneur Docker ChromaDB pour l'indexation sémantique profonde.
    - Actions d'ouverture de fichiers et de localisation instantanées.
    """
    _instance: Optional["RAGClient"] = None

    @classmethod
    def get_instance(cls) -> "RAGClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.local_indexer = LocalRAGIndexer.get_instance()
        self.docker_available = False
        self._check_docker_service()

    def _check_docker_service(self) -> bool:
        """Vérifie si le conteneur Docker ChromaDB est en ligne."""
        try:
            req = urllib.request.Request(f"{CHROMA_URL}/heartbeat", headers={"User-Agent": "AntigravityIsland"})
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                if resp.status == 200:
                    self.docker_available = True
                    return True
        except Exception:
            pass
        self.docker_available = False
        return False

    def search_files(self, query: str, limit: int = 5) -> List[Dict]:
        """Recherche de fichiers en moins de 0.005s."""
        return self.local_indexer.search(query, limit=limit)

    def find_and_open_file(self, query: str) -> Tuple[bool, str]:
        """Recherche un fichier par son nom ou description et l'ouvre immédiatement."""
        results = self.search_files(query, limit=3)
        if not results:
            return False, f"Aucun fichier trouvé correspondant à « {query} »."

        best = results[0]
        file_path = best["path"]
        try:
            os.startfile(file_path)
            return True, f"Fichier ouvert : {best['name']}"
        except Exception as e:
            return False, f"Impossible d'ouvrir {best['name']} : {e}"

    def locate_in_explorer(self, query: str) -> Tuple[bool, str]:
        """Localise et sélectionne le fichier directement dans l'Explorateur Windows."""
        results = self.search_files(query, limit=1)
        if not results:
            return False, f"Fichier introuvable pour « {query} »."

        best = results[0]
        file_path = best["path"]
        try:
            subprocess.Popen(["explorer.exe", f"/select,{file_path}"])
            return True, f"Fichier sélectionné dans l'Explorateur : {best['name']}"
        except Exception as e:
            return False, f"Erreur Explorateur : {e}"
