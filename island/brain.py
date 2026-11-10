import os
import re
import datetime
import random
import time
from typing import Optional, Callable
from island.agy_daemon import AgyDaemon

def query_agy_llm(user_query: str, timeout: int = 25, on_chunk: Optional[Callable[[str], None]] = None) -> str:
    """
    Interroge le LLM Antigravity officiel via le démon ACP persistant (même architecture qu'Open Design).
    L'instance du modèle reste chaude et vivante en arrière-plan pendant toute la vie de l'app.
    """
    daemon = AgyDaemon.get_instance()
    try:
        t0 = time.time()
        resp = daemon.ask(user_query, on_chunk=on_chunk, timeout=timeout)
        if resp:
            print(f"[Brain AGY] Réponse ACP générée en {time.time() - t0:.2f}s : '{resp}'")
            return resp
    except Exception as e:
        print(f"[Brain AGY] Erreur démon : {e}")

    return ""

def generate_response(query: str, on_chunk: Optional[Callable[[str], None]] = None) -> str:
    """
    Moteur conversationnel hybrid pour Antigravity Island.
    1. Répond instantanément aux requêtes courantes locales (salutations, heure, date, statut, blague) en 0.01s.
    2. Interroge le démon persistant agy ACP pour toute question intelligente ou ouverte.
    3. Dispose d'un fallback dynamique élégant en cas d'indisponibilité.
    """
    if not query or not query.strip():
        return "Je ne vous ai pas bien entendu. Parlez en maintenant Win + Alt."

    q = query.lower().strip()

    # 1. Salutations rapides (0.01s)
    if any(w in q for w in ["bonjour", "salut", "coucou", "hello", "bonsoir"]) and len(q.split()) <= 4:
        greetings = [
            "Bonjour ! Je suis Antigravity, à votre écoute.",
            "Salut ! Comment puis-je vous aider aujourd'hui ?",
            "Bonjour ! Je suis bien là, que puis-je faire pour vous ?"
        ]
        return random.choice(greetings)

    # 2. Heure exacte locale
    if any(w in q for w in ["heure", "quelle heure"]):
        now = datetime.datetime.now()
        return f"Il est actuellement {now.strftime('%Hh%M')}."

    # 3. Date exacte locale
    if any(w in q for w in ["date", "quel jour", "aujourd'hui"]):
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        now = datetime.datetime.now()
        nom_jour = jours[now.weekday()]
        nom_mois = mois[now.month - 1]
        return f"Nous sommes le {nom_jour} {now.day} {nom_mois} {now.year}."

    # 4. État / Forme
    if any(w in q for w in ["comment vas-tu", "comment ca va", "ca va", "ça va", "tu vas bien"]) and len(q.split()) <= 4:
        return "Je fonctionne parfaitement ! Prêt pour toutes vos requêtes."

    # 5. Blague rapide
    if any(w in q for w in ["blague", "rigoler", "drôle", "humour"]):
        jokes = [
            "Que dit une imprimante qui tombe dans l'eau ? J'ai papier !",
            "Pourquoi les développeurs détestent la nature ? Il y a trop de bugs !",
            "Que fait un geek quand il a froid ? Il se met près du pare-feu !"
        ]
        return random.choice(jokes)

    # 6. Appel au démon persistant agy (ACP streamé)
    llm_resp = query_agy_llm(query, timeout=25, on_chunk=on_chunk)
    if llm_resp:
        return llm_resp

    # 7. Fallback contextuel élégant
    return f"Bien reçu : « {query} ». Je reste à vos côtés."
