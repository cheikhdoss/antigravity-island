import datetime
import random
import re

def generate_response(query: str) -> str:
    """
    Moteur conversationnel intelligent et réactif pour Antigravity Island.
    Répond instantanément et précisément aux requêtes vocales de l'utilisateur en français.
    """
    if not query or not query.strip():
        return "Je ne vous ai pas bien entendu. Parlez en maintenant Win + Alt."

    q = query.lower().strip()

    # 1. Salutations
    if any(w in q for w in ["bonjour", "salut", "coucou", "hello", "bonsoir"]):
        greetings = [
            "Bonjour ! Je suis Antigravity, à votre écoute.",
            "Salut ! Comment puis-je vous aider aujourd'hui ?",
            "Bonjour ! Je suis bien là, que puis-je faire pour vous ?"
        ]
        return random.choice(greetings)

    # 2. Identité
    if any(w in q for w in ["qui es-tu", "qui est tu", "tu es qui", "c'est quoi", "présente-toi", "presente toi"]):
        return "Je suis Antigravity Island, votre compagnon de bureau intelligent pour Windows."

    # 3. Comment ça va / État
    if any(w in q for w in ["comment vas-tu", "comment ca va", "ca va", "ça va", "tu vas bien"]):
        return "Je fonctionne parfaitement ! Prêt pour toutes vos requêtes."

    # 4. Heure
    if any(w in q for w in ["heure", "quelle heure"]):
        now = datetime.datetime.now()
        return f"Il est actuellement {now.strftime('%Hh%M')}."

    # 5. Date
    if any(w in q for w in ["date", "quel jour", "aujourd'hui"]):
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        now = datetime.datetime.now()
        nom_jour = jours[now.weekday()]
        nom_mois = mois[now.month - 1]
        return f"Nous sommes le {nom_jour} {now.day} {nom_mois} {now.year}."

    # 6. Remerciements
    if any(w in q for w in ["merci", "super", "parfait", "génial", "top"]):
        return "Avec grand plaisir ! Dites-moi si vous avez besoin d'autre chose."

    # 7. Blague / Humour
    if any(w in q for w in ["blague", "rigoler", "drôle", "humour"]):
        jokes = [
            "Que dit une imprimante qui tombe dans l'eau ? J'ai papier !",
            "Pourquoi les développeurs détestent la nature ? Il y a trop de bugs !",
            "Que fait un geek quand il a froid ? Il se met près du pare-feu !"
        ]
        return random.choice(jokes)

    # 8. Commandes système de base
    if "ferme" in q or "quitte" in q:
        return "Pour fermer, faites un clic droit sur l'encoche et choisissez Quitter."

    if "paramètre" in q or "centre de contrôle" in q or "reglage" in q:
        return "Cliquez simplement sur l'encoche pour ouvrir le Centre de contrôle."

    # 9. Question d'aide ou de capacités
    if any(w in q for w in ["aide", "peux-tu faire", "tu sais faire", "capacités"]):
        return "Je peux surveiller votre écran, piloter la souris, cliquer, taper du texte et répondre à vos questions."

    # 10. Réponse contextuelle générique élégante
    return f"Bien reçu : « {query} ». Je reste à vos côtés."
