import os
import re
import math
import datetime
import random
import time
from typing import Optional, Callable
from island.agy_daemon import AgyDaemon

def solve_instant_math(query: str) -> Optional[str]:
    """Résout les opérations mathématiques courantes en 0.001s sans solliciter le LLM."""
    q = query.lower().strip()
    
    # Remplacements textuels français et suppression des préfixes conversationnels
    q_calc = q.replace("combien font", "").replace("calcule", "").replace("égal", "")
    q_calc = q_calc.replace("j'ai dit", "").replace("je dis", "").replace("qu'est-ce que", "")
    q_calc = q_calc.replace("fois", "*").replace("x", "*").replace("multiplier par", "*")
    q_calc = q_calc.replace("divisé par", "/").replace("sur", "/")
    q_calc = q_calc.replace("plus", "+").replace("et", "+")
    q_calc = q_calc.replace("moins", "-")
    q_calc = q_calc.replace(",", ".")
    q_calc = q_calc.strip()

    # Si c'est incomplet (ex: "j'ai dit 2 +" ou "2 *")
    m_inc = re.search(r'(\d+(?:\.\d+)?)\s*([\*\+\-\/])\s*$', q_calc)
    if m_inc:
        num, op = m_inc.groups()
        op_nom = "additionner" if op == "+" else ("multiplier" if op == "*" else ("soustraire" if op == "-" else "diviser"))
        return f"Par combien voulez-vous {op_nom} avec {num} ? Donnez-moi le second nombre."

    # Pattern d'expression arithmétique simple
    match = re.search(r'(\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(\d+(?:\.\d+)?)', q_calc)
    if match:
        a_str, op, b_str = match.groups()
        try:
            a = float(a_str)
            b = float(b_str)
            if op == "+":
                res = a + b
            elif op == "-":
                res = a - b
            elif op == "*":
                res = a * b
            elif op == "/":
                if b == 0:
                    return "Division par zéro impossible."
                res = a / b
            else:
                return None
            
            # Formatage élégant
            res_str = f"{int(res)}" if res.is_integer() else f"{res:.2f}"
            a_fmt = f"{int(a)}" if a.is_integer() else f"{a}"
            b_fmt = f"{int(b)}" if b.is_integer() else f"{b}"
            op_symbol = "×" if op == "*" else ("÷" if op == "/" else op)
            return f"{a_fmt} {op_symbol} {b_fmt} = {res_str}"
        except Exception:
            pass

    return None

def query_agy_llm(user_query: str, timeout: int = 30, on_chunk: Optional[Callable[[str], None]] = None) -> str:
    """
    Interroge le démon agy avec streaming live et timeout sécurisé (30s).
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
    Moteur conversationnel ultra-rapide (<0.01s en local, <1.5s via ACP).
    """
    if not query or not query.strip():
        return "Je ne vous ai pas bien entendu. Maintenez Win + Alt et parlez."

    q = query.lower().strip()

    # 1. Calculs mathématiques instantanés (0.001s)
    math_res = solve_instant_math(q)
    if math_res:
        return math_res

    # 2. Salutations rapides (0.001s)
    if any(w in q for w in ["bonjour", "salut", "coucou", "hello", "bonsoir"]) and len(q.split()) <= 4:
        greetings = [
            "Bonjour ! Je suis Antigravity, à vos côtés.",
            "Salut ! Prêt pour vos requêtes.",
            "Bonjour ! Que puis-je faire pour vous ?"
        ]
        return random.choice(greetings)

    # 3. Heure exacte locale (0.001s)
    if any(w in q for w in ["heure", "quelle heure"]):
        now = datetime.datetime.now()
        return f"Il est actuellement {now.strftime('%Hh%M')}."

    # 4. Date exacte locale (0.001s)
    if any(w in q for w in ["date", "quel jour", "aujourd'hui"]):
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        now = datetime.datetime.now()
        return f"Nous sommes le {jours[now.weekday()]} {now.day} {mois[now.month - 1]} {now.year}."

    # 5. Identité & Capacité (0.001s)
    if any(w in q for w in ["qui es-tu", "qui es tu", "c'est quoi cette encoche", "t'es qui"]):
        return "Je suis Antigravity Island : votre Dynamic Island intelligente sur Windows."

    if any(w in q for w in ["que sais-tu faire", "que peux-tu faire", "aide-moi", "fonctionnalités"]):
        return "Je surveille vos notifications, range vos fenêtres réduites et réponds à toutes vos questions."

    # 6. État / Forme (0.001s)
    if any(w in q for w in ["comment vas-tu", "comment ca va", "ca va", "ça va", "tu vas bien"]) and len(q.split()) <= 4:
        return "Je fonctionne parfaitement ! Prêt pour vos requêtes."

    # 7. Blague rapide (0.001s)
    if any(w in q for w in ["blague", "rigoler", "drôle", "humour"]):
        jokes = [
            "Que dit une imprimante qui tombe dans l'eau ? J'ai papier !",
            "Pourquoi les développeurs détestent la nature ? Il y a trop de bugs !",
            "Que fait un geek quand il a froid ? Il se met près du pare-feu !"
        ]
        return random.choice(jokes)

    # 8. Appel au démon persistant agy (ACP rapide avec streaming)
    llm_resp = query_agy_llm(query, timeout=30, on_chunk=on_chunk)
    if llm_resp:
        return llm_resp

    # 9. Fallback direct et élégant
    return f"Bien reçu : « {query} ». Je reste à vos côtés."
