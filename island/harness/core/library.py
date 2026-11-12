# Copyright 2026 Google LLC - Harness² Architecture
# Adapted for Antigravity Island Autonomous Desktop Operations

import os
import re
import json
import time
from pathlib import Path
from typing import List, Dict, Optional

def slug(task_id: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]', '_', task_id)

def has_experience(exp: dict) -> bool:
    return isinstance(exp, dict) and all(
        isinstance(exp.get(k), str) and exp[k].strip()
        for k in ("cue", "lesson", "evidence")
    )

class ExperienceLibrary:
    """
    Bibliothèque d'expériences persistantes Harness² (Google Research).
    Stocke durablement les apprentissages récursifs de l'Island :
    - <root>/<domain>/INDEX.md
    - <root>/<domain>/experiences/<task_id>/EXPERIENCE.md
    Chaque expérience contient un déclencheur (cue), la leçon apprise (lesson)
    et les preuves factuelles d'exécution (evidence).
    """

    def __init__(self, root_dir: Optional[str] = None):
        if not root_dir:
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            root_dir = os.path.join(appdata, "AntigravityIsland", "harness_library")
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.experiences_cache: List[Dict] = []
        self._load_all_experiences()

    def _domain_dir(self, domain: str) -> Path:
        clean_domain = re.sub(r'\s*[/\\]\s*', '__', domain).strip() or "general"
        d = self.root / clean_domain
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _load_all_experiences(self):
        self.experiences_cache = []
        for index_file in self.root.glob("*/INDEX.md"):
            try:
                content = index_file.read_text(encoding="utf-8")
                # Parser les blocs d'expérience
                pattern = r'<experience>\s*<cue>(.*?)</cue>\s*<lesson>(.*?)</lesson>\s*<evidence>(.*?)</evidence>\s*</experience>'
                matches = re.findall(pattern, content, flags=re.DOTALL)
                for cue, lesson, evidence in matches:
                    self.experiences_cache.append({
                        "domain": index_file.parent.name,
                        "cue": cue.strip(),
                        "lesson": lesson.strip(),
                        "evidence": evidence.strip(),
                        "timestamp": index_file.stat().st_mtime
                    })
            except Exception as e:
                print(f"[Harness Library] Erreur lecture {index_file} : {e}")

    def find_relevant_lessons(self, query: str, domain: str = "general", limit: int = 3) -> List[Dict]:
        """Retrouve en <0.001s les leçons apprises pertinentes pour une requête donnée."""
        tokens = set(re.findall(r'\w+', query.lower()))
        scored = []
        for exp in self.experiences_cache:
            cue_tokens = set(re.findall(r'\w+', exp["cue"].lower()))
            overlap = len(tokens & cue_tokens)
            if overlap > 0:
                score = overlap * 10
                if exp["domain"] == domain:
                    score += 15
                scored.append((score, exp))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def record_experience(self, cue: str, lesson: str, evidence: str, domain: str = "general", task_id: str = "task"):
        """Consigne une nouvelle expérience validée dans la bibliothèque Harness²."""
        d_path = self._domain_dir(domain)
        index_path = d_path / "INDEX.md"

        exp_entry = (
            f"\n<experience>\n"
            f"  <cue>{cue.strip()}</cue>\n"
            f"  <lesson>{lesson.strip()}</lesson>\n"
            f"  <evidence>{evidence.strip()}</evidence>\n"
            f"</experience>\n"
        )

        try:
            with open(index_path, "a", encoding="utf-8") as f:
                f.write(exp_entry)

            # Création du dossier d'archive de tâche
            task_dir = d_path / "experiences" / slug(task_id)
            task_dir.mkdir(parents=True, exist_ok=True)
            exp_file = task_dir / "EXPERIENCE.md"
            with open(exp_file, "w", encoding="utf-8") as f:
                f.write(f"# Expérience Harness² — {task_id}\n")
                f.write(f"- **Date** : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"- **Domaine** : {domain}\n\n")
                f.write(exp_entry)

            # Mettre à jour le cache
            self.experiences_cache.append({
                "domain": domain,
                "cue": cue.strip(),
                "lesson": lesson.strip(),
                "evidence": evidence.strip(),
                "timestamp": time.time()
            })
            print(f"[Harness Library] Expérience consignée avec succès pour le domaine '{domain}'")
        except Exception as e:
            print(f"[Harness Library] Erreur écriture expérience : {e}")
