import os
import re
import datetime
import random
import subprocess
import time

AGY_PATH = r"C:\Users\pro\AppData\Local\agy\bin\agy.EXE"

def query_agy_llm(user_query: str, timeout: int = 18) -> str:
    """
    Interroge le LLM Antigravity officiel via agy CLI pour obtenir une réponse intelligente.
    """
    if not os.path.exists(AGY_PATH):
        return ""

    system_instruction = (
        "Consigne: Tu es Antigravity Island, le compagnon desktop intelligent de l'utilisateur. "
        "Réponds en français de manière directe, naturelle et concise (maximum 1 ou 2 phrases percutantes, adaptées à la voix). "
        "Ne mets aucun emoji, pas de code ni de markdown lourd.\n"
        f"Question: {user_query}\n"
        "Réponse:"
    )

    cmd = [
        AGY_PATH,
        "--new-project",
        "--print", system_instruction,
        "--disable-slash-commands",
        "--effort", "low",
        "--output-format", "text"
    ]

    try:
        t0 = time.time()
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=0x08000000  # CREATE_NO_WINDOW : aucun clignotement de terminal
        )
        if res.returncode == 0 and res.stdout.strip():
            raw = res.stdout.strip()
            # Nettoyer les éventuels préfixes "Réponse :" ou guillemets superflus
            clean = re.sub(r'^(Antigravity\s*:|Réponse\s*:|Ta réponse\s*:)\s*', '', raw, flags=re.IGNORECASE)
            print(f"[Brain AGY] Réponse LLM générée en {time.time() - t0:.2f}s : '{clean}'")
            return clean.strip()
    except subprocess.TimeoutExpired:
        print(f"[Brain AGY] Timeout après {timeout}s")
    except Exception as e:
        print(f"[Brain AGY] Erreur CLI : {e}")

    return ""

def generate_response(query: str) -> str:
    """
    Moteur conversationnel hybrid pour Antigravity Island.
    1. Répond instantanément aux requêtes courantes (salutations, heure, date, statut).
    2. Interroge le modèle agy CLI pour toute question complexe ou ouverte.
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

    # 6. Appel au LLM Antigravity officiel (agy CLI)
    llm_resp = query_agy_llm(query, timeout=18)
    if llm_resp:
        return llm_resp

    # 7. Fallback contextuel élégant
    return f"Bien reçu : « {query} ». Je reste à vos côtés."
