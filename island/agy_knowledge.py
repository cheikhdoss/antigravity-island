import os
import sys
import time
import datetime
import ctypes
from typing import Optional, Dict, Any

class AgyKnowledge:
    """
    Moteur de Connaissances, d'Intelligence et de Compétences pour l'Agent Antigravity (AGY).
    Fournit à la fonction AGY un savoir encyclopédique de l'environnement de l'utilisateur,
    de ses projets logiciels, du contrôle système de Windows et du contexte temps réel.
    """

    USER_PROFILE = {
        "name": "Cheikh Tidiane Mbodj",
        "username": "cheikhdoss",
        "email": "cmbodj@groupeisi.com",
        "role": "Ingénieur Logiciel & Tech Innovator",
        "location": "Dakar, Sénégal",
        "languages": ["Français", "Wolof", "Anglais"],
        "stack": ["Flutter", "Supabase", "TypeScript", "React", "Python", "Spring Boot", "Fastify", "Docker", "Git", "PowerShell"],
    }

    PROJECTS = {
        "senstory": {
            "name": "SenStory",
            "desc": "Plateforme mobile et web de récits de vie et confessions anonymes au Sénégal avec groupes privés éphémères, réactions Twemoji SVG, feed public et traçabilité IP.",
            "tech": "Flutter Web/Mobile + Supabase Auth / PostgreSQL avec RLS strict.",
            "path": r"C:\Users\pro\second-brain\001-PROJECTS\SenStory.md"
        },
        "samapdf": {
            "name": "SamaPdf",
            "desc": "Suite bureautique et plateforme de conversion/édition documentaire PDF pour entreprises avec éditeur OnlyOffice Document Server 9.x, moteur Gotenberg et OCR.",
            "tech": "Spring Boot (Backend) + React / Vite / Tailwind (Frontend) + Nginx + Cloudflare."
        },
        "samatop": {
            "name": "SamaTop",
            "desc": "Studio de génération de séries dramatiques par IA avec synchronisation des voix d'acteurs en Wolof, prompts de tournage Google Flow et moteur Agnes AI.",
            "tech": "Fastify (:8095) + Vite (:5190) + Design System SamaTop / TasteSkill v1."
        },
        "second_brain": {
            "name": "Second Brain (Obsidian Vault)",
            "desc": "Système de mémoire globale, base de connaissances Zettelkasten, journal de bord 00-SESSION-LOG.md et notes quotidiennes 005-DAILY.",
            "path": r"C:\Users\pro\second-brain"
        },
        "antigravity_island": {
            "name": "Antigravity Island",
            "desc": "Encoche dynamique intelligente pour Windows (fusion Dynamic Island, HeyClicky et Agent-Desktop) avec assistant de cours/réunion Meet, vision multimodale et contrôle vocal.",
            "path": r"C:\Users\pro\.gemini\antigravity\scratch\antigravity-island",
            "hotkeys": {
                "vocal_ptt": "Win + Alt (Maintenir pour parler)",
                "meet_mode": "Win + Alt + M (Assistant de réunion/cours en direct)",
                "control_hub": "Win + Alt + H (Déployer le hub d'outils)",
                "click": "Clic sur l'encoche pour ouvrir le Hub"
            }
        }
    }

    @staticmethod
    def get_foreground_window_title() -> str:
        """Récupère le titre et l'application au premier plan sous Windows en <1ms."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return "Bureau Windows"
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return "Bureau Windows"
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()
            return title if title else "Bureau Windows"
        except Exception:
            return "Bureau Windows"

    @classmethod
    def get_runtime_context(cls) -> str:
        """Génère le contexte temps réel dynamique du système pour l'assistant."""
        now = datetime.datetime.now()
        days_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        months_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        date_str = f"{days_fr[now.weekday()]} {now.day} {months_fr[now.month - 1]} {now.year} à {now.strftime('%H:%M')}"

        fg_window = cls.get_foreground_window_title()

        return (
            f"--- CONTEXTE SYSTÈME TEMPS RÉEL ---\n"
            f"- Date et heure actuelles : {date_str}\n"
            f"- Fenêtre active au premier plan : « {fg_window} »\n"
            f"- Système d'exploitation : Windows 10/11 Pro (Utilisateur: {cls.USER_PROFILE['name']})\n"
            f"------------------------------------"
        )

    @classmethod
    def build_system_prompt(cls, is_vision: bool = False) -> str:
        """Construit le prompt d'intelligence supérieure pour le démon AGY."""
        user = cls.USER_PROFILE

        prompt = (
            f"Tu es Antigravity Island AGY, l'intelligence artificielle centrale de l'encoche dynamique sur Windows.\n"
            f"Tu es l'assistant personnel d'élite de {user['name']} ({user['username']}), {user['role']} basé à {user['location']}.\n\n"
            f"SAVOIR SUR LES PROJETS DE CHEIKH :\n"
            f"1. SenStory : Réseau social sénégalais de récits de vie et confessions anonymes (Flutter + Supabase Auth/PostgreSQL, RLS strict, groupes éphémères, réactions Twemoji SVG, feed public, traçabilité IP).\n"
            f"2. SamaPdf : Plateforme professionnelle de conversion et édition PDF (OnlyOffice Document Server 9.x, Gotenberg, OCR Tesseract, Spring Boot, React).\n"
            f"3. SamaTop : Studio IA de création de séries dramatiques (Google Flow, Agnes AI, répliques en Wolof, Fastify, Vite).\n"
            f"4. Second Brain (Obsidian Vault à {cls.PROJECTS['second_brain']['path']}) : Base Zettelkasten, journal global 00-SESSION-LOG.md, notes quotidiennes 005-DAILY.\n"
            f"5. Antigravity Island : L'encoche dynamique active sur son écran (Win+Alt pour parler, Win+Alt+M pour le Mode Meet, Win+Alt+H pour le Hub).\n\n"
            f"COMPÉTENCES DE CONTRÔLE BUREAU (COMPUTER USE) :\n"
            f"Tu as le pouvoir d'agir directement sur l'ordinateur de l'utilisateur.\n"
            f"Si la demande nécessite d'agir sur le système (ouvrir un logiciel, naviguer sur le web, changer le son, ouvrir un projet, fermer une fenêtre, pointer un élément sur l'écran, vider la corbeille, faire une capture), tu DOIS répondre avec un bloc JSON d'action strict au format suivant :\n"
            f"```json\n"
            f"{{\n"
            f'  "action": "open_app | open_project | close_app | minimize_app | set_volume | media_control | browse_web | take_screenshot | point_at | click | type_text | empty_recycle_bin | run_powershell",\n'
            f'  "params": {{ ... }},\n'
            f'  "say": "Courte confirmation parlée en français (ex: \'J\\\'ouvre SenStory\', \'Volume réglé à 50%\')"\n'
            f"}}\n"
            f"```\n\n"
            f"Exemples de paramètres d'action :\n"
            f"- open_app: {{\"name\": \"chrome\" | \"code\" | \"phpstorm\" | \"terminal\" | \"spotify\" | \"calculatrice\" | \"bloc-notes\" | \"explorateur\"}}\n"
            f"- open_project: {{\"name\": \"senstory\" | \"samapdf\" | \"samatop\" | \"second-brain\" | \"island\"}}\n"
            f"- close_app: {{\"name\": \"active\" | \"nom_app\"}}\n"
            f"- minimize_app: {{\"name\": \"active\"}}\n"
            f"- set_volume: {{\"level\": 0-100}}\n"
            f"- media_control: {{\"command\": \"play_pause\" | \"next\" | \"prev\"}}\n"
            f"- browse_web: {{\"query\": \"recherche\", \"site\": \"google\" | \"youtube\" | \"github\" | \"direct\"}}\n"
            f"- take_screenshot: {{}}\n"
            f"- point_at: {{\"target\": \"nom ou texte de l'élément à pointer avec le halo HeyClicky\"}}\n"
            f"- run_powershell: {{\"command\": \"commande powershell sûre\"}}\n\n"
            f"INTELLIGENCE ET STYLE DE RÉPONSE :\n"
            f"- Si la demande est une question informative, de réflexion, d'architecture, de code ou d'aide : réponds avec une haute intelligence, rigueur et concision percutante en français (1 à 3 phrases claires adaptées à l'affichage dynamique et à la synthèse vocale, sans préambule inutile ni astérisques markdown excessifs).\n"
            f"- Comprends parfaitement le français, le wolof et l'anglais technique.\n"
            f"- Reste toujours proactif, précis et au service de Cheikh."
        )

        if is_vision:
            prompt += (
                f"\n\nMODE VISION MULTIMODALE :\n"
                f"Tu reçois la capture d'écran actuelle de l'utilisateur. Analyse avec acuité les éléments affichés (code, bugs, terminaux, applications, pages web, documents) et réponds directement avec perspicacité et pertinence."
            )

        return prompt

    @classmethod
    def format_user_prompt(cls, user_query: str, conversation_history: str = "") -> str:
        """Formate le prompt complet envoyé à AGY en intégrant contexte, mémoire et requête."""
        runtime_ctx = cls.get_runtime_context()
        sys_prompt = cls.build_system_prompt(is_vision=False)

        history_block = f"\nHISTORIQUE RÉCENT :\n{conversation_history.strip()}\n" if conversation_history and conversation_history.strip() else ""

        full_prompt = (
            f"{sys_prompt}\n\n"
            f"{runtime_ctx}\n"
            f"{history_block}\n"
            f"DEMANDE DE L'UTILISATEUR :\n{user_query.strip()}"
        )
        return full_prompt

    @classmethod
    def format_vision_prompt(cls, user_query: str) -> str:
        """Formate le prompt pour l'analyse visuelle multimodale AGY."""
        runtime_ctx = cls.get_runtime_context()
        sys_prompt = cls.build_system_prompt(is_vision=True)

        q = user_query.strip() if user_query and user_query.strip() else "Analyse ce que tu vois à l'écran."

        full_prompt = (
            f"{sys_prompt}\n\n"
            f"{runtime_ctx}\n\n"
            f"QUESTION SUR L'ÉCRAN :\n{q}"
        )
        return full_prompt
