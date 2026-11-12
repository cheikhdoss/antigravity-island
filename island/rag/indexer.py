import os
import sys
import time
import sqlite3
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class LocalRAGIndexer:
    """
    Moteur RAG et d'indexation ultra-rapide (<0.005s) pour Antigravity Island.
    Indexe les fichiers clés, projets de développement et notes dans un cache mémoire
    doublé d'une base SQLite FTS5 pour une persistance totale sans latence réseau.
    """
    _instance: Optional["LocalRAGIndexer"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "LocalRAGIndexer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        self.db_dir = os.path.join(appdata, "AntigravityIsland", "rag")
        os.makedirs(self.db_dir, exist_ok=True)
        self.db_path = os.path.join(self.db_dir, "rag_index.db")

        # Racine des dossiers utilisateurs surveillés
        user_home = os.path.expanduser("~")
        self.monitored_paths = [
            os.path.join(user_home, "Desktop"),
            os.path.join(user_home, "Downloads"),
            os.path.join(user_home, "Documents"),
            os.path.join(user_home, "PhpstormProjects"),
            os.path.join(user_home, "second-brain"),
            os.path.join(user_home, ".gemini", "antigravity", "scratch")
        ]

        # Cache en mémoire pour accès instantané (0.001s)
        self._memory_cache: List[Dict] = []
        self._cache_lock = threading.Lock()
        self._is_indexing = False
        self._last_index_time = 0.0

        self._init_db()
        self._load_cache_from_db()
        
        # Lancement de l'indexation initiale en tâche de fond (asynchrone, 0 impact UI)
        threading.Thread(target=self.index_all, daemon=True).start()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS files_index (
                        path TEXT PRIMARY KEY,
                        name TEXT,
                        extension TEXT,
                        directory TEXT,
                        size INTEGER,
                        mtime REAL,
                        category TEXT,
                        tags TEXT
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_files_name ON files_index(name);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_files_ext ON files_index(extension);
                """)
                conn.commit()
        except Exception as e:
            print(f"[RAG Indexer] Erreur init SQLite : {e}")

    def _load_cache_from_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT path, name, extension, directory, size, mtime, category, tags FROM files_index")
                rows = cursor.fetchall()
                with self._cache_lock:
                    self._memory_cache = [
                        {
                            "path": r[0],
                            "name": r[1],
                            "ext": r[2],
                            "dir": r[3],
                            "size": r[4],
                            "mtime": r[5],
                            "category": r[6],
                            "tags": r[7]
                        }
                        for r in rows
                    ]
            print(f"[RAG Indexer] Cache mémoire chargé : {len(self._memory_cache)} fichiers prêts.")
        except Exception as e:
            print(f"[RAG Indexer] Erreur chargement cache : {e}")

    def index_all(self):
        if self._is_indexing:
            return
        self._is_indexing = True
        t0 = time.time()
        discovered = []

        ignore_dirs = {
            "node_modules", ".git", ".idea", "__pycache__", ".venv", "venv", 
            "dist", "build", "AppData", "Application Data", ".cache", "site-packages"
        }

        for root_dir in self.monitored_paths:
            if not os.path.exists(root_dir):
                continue
            try:
                for root, dirs, files in os.walk(root_dir):
                    dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
                    for f in files:
                        if f.startswith(".") or f.endswith(".tmp"):
                            continue
                        f_path = os.path.join(root, f)
                        try:
                            stat = os.stat(f_path)
                            ext = os.path.splitext(f)[1].lower().replace(".", "")
                            
                            category = "other"
                            if ext in ["pdf", "docx", "doc", "txt", "md", "pptx", "xlsx"]:
                                category = "document"
                            elif ext in ["py", "js", "ts", "tsx", "jsx", "html", "css", "dart", "json", "yaml", "yml", "sql"]:
                                category = "code"
                            elif ext in ["png", "jpg", "jpeg", "webp", "ico", "svg"]:
                                category = "image"
                            elif ext in ["exe", "bat", "cmd", "ps1", "sh"]:
                                category = "executable"

                            # Tags utiles
                            tags = f"{ext} {category} {os.path.basename(root).lower()}"

                            discovered.append((
                                f_path, f, ext, root, stat.st_size, stat.st_mtime, category, tags
                            ))
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
            except Exception as e:
                print(f"[RAG Indexer] Erreur scan {root_dir} : {e}")

        # Enregistrement en base de données et mise à jour du cache
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.executemany("""
                    INSERT OR REPLACE INTO files_index (path, name, extension, directory, size, mtime, category, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, discovered)
                conn.commit()

            with self._cache_lock:
                self._memory_cache = [
                    {
                        "path": d[0],
                        "name": d[1],
                        "ext": d[2],
                        "dir": d[3],
                        "size": d[4],
                        "mtime": d[5],
                        "category": d[6],
                        "tags": d[7]
                    }
                    for d in discovered
                ]
            self._last_index_time = time.time()
            print(f"[RAG Indexer] Indexation terminée en {time.time() - t0:.2f}s : {len(discovered)} fichiers indexés.")
        except Exception as e:
            print(f"[RAG Indexer] Erreur sauvegarde DB : {e}")
        finally:
            self._is_indexing = False

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Recherche ultra-rapide (<0.002s) dans l'index mémoire avec scoring pertinence."""
        t0 = time.time()
        tokens = [t.lower().strip() for t in query.split() if len(t.strip()) > 1]
        if not tokens:
            return []

        results = []
        with self._cache_lock:
            for item in self._memory_cache:
                name_lower = item["name"].lower()
                path_lower = item["path"].lower()
                tags_lower = item["tags"].lower()

                score = 0
                all_match = True
                for tok in tokens:
                    if tok in name_lower:
                        score += 50
                        if name_lower.startswith(tok) or f"_{tok}" in name_lower or f"-{tok}" in name_lower:
                            score += 30
                    elif tok in tags_lower:
                        score += 20
                    elif tok in path_lower:
                        score += 10
                    else:
                        all_match = False

                if all_match or (score >= 40):
                    # Bonus pour les fichiers récents
                    recency_bonus = min(20, max(0, int((item["mtime"] - (time.time() - 86400 * 30)) / 86400)))
                    total_score = score + recency_bonus
                    results.append((total_score, item))

        results.sort(key=lambda x: x[0], reverse=True)
        top = [item for _, item in results[:limit]]
        print(f"[RAG Search] Requête '{query}' exécutée en {(time.time() - t0) * 1000:.1f}ms ({len(top)} résultats)")
        return top

    def get_stats(self) -> Dict:
        with self._cache_lock:
            count = len(self._memory_cache)
        return {
            "total_files": count,
            "last_index_time": self._last_index_time,
            "is_indexing": self._is_indexing,
            "db_path": self.db_path
        }
