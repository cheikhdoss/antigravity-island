import os
import re
import math
import datetime
import random
import time
import json
import urllib.request
import base64
import io
from typing import Optional, Callable, List, Dict
from island.agy_daemon import AgyDaemon
from island.desktop_control import DesktopController

NIM_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NIM_API_KEY = "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"
AGNES_API_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
AGNES_API_KEY = "sk-B34o3ZnpLfcCa7KtTI67fthOkJ6dQvhEmKjsiRvTZnKl5FlE"
DEFAULT_NIM_MODEL = "nvidia/nemotron-3.5-bolt-e4b"

def get_current_nim_model() -> str:
    """Lit le modèle NVIDIA NIM configuré dans settings.json parmi les 5 modèles benchmarkés."""
    try:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        settings_path = os.path.join(appdata, "AntigravityIsland", "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                return data.get("nim_model", DEFAULT_NIM_MODEL)
    except Exception:
        pass
    return DEFAULT_NIM_MODEL

def get_current_vision_provider() -> str:
    """Lit le fournisseur de vision configuré dans settings.json ('agnes', 'nim_vl', 'ocr')."""
    try:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        settings_path = os.path.join(appdata, "AntigravityIsland", "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                return data.get("vision_provider", "agnes")
    except Exception:
        pass
    return "agnes"

def get_current_provider() -> str:
    """Lit le fournisseur configuré dans settings.json ('agnes', 'nim', 'agy'). Par défaut: agnes."""
    try:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        settings_path = os.path.join(appdata, "AntigravityIsland", "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                return data.get("llm_provider", "agnes")
    except Exception:
        pass
    return "agnes"

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

def capture_screen_base64() -> Optional[str]:
    """Capture l'écran actif et le compresse en JPEG 1280x720 base64 data URL pour l'analyse visuelle ultra-rapide."""
    try:
        import mss
        from PIL import Image
        with mss.MSS() as sct:
            mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            sct_img = sct.grab(mon)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.thumbnail((1280, 720))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64_data}"
    except Exception as e:
        print("[Brain Vision] Erreur capture écran MSS:", e)
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=True)
            img.thumbnail((1280, 720))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64_data}"
        except Exception as e2:
            print("[Brain Vision] Erreur capture écran PIL:", e2)
    return None

def query_vision_model(prompt: str, on_chunk: Optional[Callable[[str], None]] = None) -> str:
    """
    Analyse l'écran ou un diagramme avec le modèle Vision sélectionné :
    - Agnes AI 3.0 Flash Vision (~1.0s, ultra-rapide)
    - NVIDIA Nemotron 3.5 Super-VL 120B (multimodal NIM de pointe)
    - WinRT OCR Local (<0.15s)
    """
    t0 = time.time()
    v_prov = get_current_vision_provider()
    print(f"[Brain Vision] Analyse visuelle initiée avec le fournisseur : {v_prov}")

    if v_prov == "ocr":
        try:
            from island.ocr import find_screen_elements
            elements = find_screen_elements("")
            if elements:
                texts = [e["text"] for e in elements[:15] if len(e.get("text", "")) > 1]
                res = "Texte et éléments identifiés à l'écran : " + ", ".join(texts)
                return res
            return "Aucun texte distinct n'a été détecté à l'écran."
        except Exception as e:
            return f"Erreur analyse OCR : {e}"

    data_url = capture_screen_base64()
    if not data_url:
        return "Impossible de capturer l'écran pour l'analyse visuelle."

    system_prompt = (
        "Tu es Antigravity Island, un assistant d'analyse visuelle ultra-rapide et précis sur Windows. "
        "L'utilisateur te demande d'analyser son écran (diagramme, schéma, interface, code, document, page web). "
        "Donne une réponse claire, directe et naturelle en français en 1 à 2 phrases percutantes, sans bavardage superflu."
    )

    if v_prov == "agnes":
        # 1. Agnes AI 3.0 Flash Vision (~1.0s)
        headers = {
            "Authorization": f"Bearer {AGNES_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "agnes-3.0-flash",
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }
            ],
            "max_tokens": 200,
            "temperature": 0.2
        }
        try:
            req = urllib.request.Request(AGNES_API_URL, json.dumps(payload).encode("utf-8"), headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ans = data["choices"][0]["message"]["content"].strip()
                print(f"[Brain Vision Agnes] Réponse en {time.time() - t0:.2f}s : '{ans}'")
                return ans
        except Exception as e:
            print(f"[Brain Vision Agnes] Erreur appel API : {e}")

    # 2. NVIDIA Nemotron 3.5 Super-VL 120B
    headers = {
        "Authorization": f"Bearer {NIM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "nvidia/nemotron-3.5-super-vl-120b-a12b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }
        ],
        "max_tokens": 400,
        "temperature": 0.2
    }
    try:
        req = urllib.request.Request(NIM_API_URL, json.dumps(payload).encode("utf-8"), headers)
        with urllib.request.urlopen(req, timeout=18) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choice = data["choices"][0]["message"]
            ans = choice.get("content") or choice.get("reasoning_content") or ""
            ans = re.sub(r'<think>.*?</think>', '', ans, flags=re.DOTALL).strip()
            print(f"[Brain Vision NIM] Réponse en {time.time() - t0:.2f}s : '{ans}'")
            if ans:
                return ans
    except Exception as e:
        print(f"[Brain Vision NIM] Erreur appel API : {e}")

    # Repli de secours OCR
    try:
        from island.ocr import find_screen_elements
        elements = find_screen_elements("")
        if elements:
            texts = [e["text"] for e in elements[:12] if len(e.get("text", "")) > 1]
            return "Éléments textuels repérés à l'écran : " + ", ".join(texts)
    except Exception:
        pass

    return "J'ai observé votre écran, aucun détail particulier n'a pu être extrait."

COMPUTER_USE_SYSTEM_PROMPT = (
    "Tu es Antigravity Island, un agent autonome d'élite de contrôle total du bureau Windows (fusion de HeyClicky et Vercel Agent-Desktop).\n"
    "Tu as un contrôle direct et entier sur la machine de l'utilisateur.\n\n"
    "RÈGLES D'ACTION :\n"
    "1. Si la demande de l'utilisateur implique d'agir sur l'ordinateur (ouvrir/fermer des applications, cliquer sur un bouton ou du texte, taper au clavier, naviguer sur le web, vider la corbeille, régler le volume, manipuler des fichiers, faire une capture d'écran, fermer des messages d'erreur, etc.), tu DOIS répondre STRICTEMENT avec un bloc JSON d'action :\n"
    "```json\n"
    "{\n"
    '  "action": "open_app | close_app | minimize_app | point_at | click | type_text | edit_text | scroll | search_in_page | press_hotkey | empty_recycle_bin | set_volume | media_control | create_file | browse_web | take_screenshot | run_powershell",\n'
    '  "params": { ... },\n'
    '  "say": "Courte confirmation en français pour la Dynamic Island (ex: \'Bloc-notes ouvert\', \'Corbeille vidée\')"\n'
    "}\n"
    "```\n\n"
    "Détails des paramètres :\n"
    "- open_app: {\"name\": \"corbeille\" | \"bloc-notes\" | \"brave\" | \"explorateur\" | \"calculatrice\" | \"paramètres\" | \"nom_app\"}\n"
    "- close_app: {\"name\": \"active\" pour la fenêtre/boîte de dialogue active, ou \"nom_app\" (ex: \"bloc-notes\")}\n"
    "- minimize_app: {\"name\": \"active\"}\n"
    "- point_at: {\"target\": \"explorateur de fichiers\" | \"icône\" | \"nom de l'élément à montrer avec le pointeur HeyClicky\"}\n"
    "- click: {\"target\": \"texte du bouton ou icône (ex: OK, Annuler)\", \"button\": \"left\"|\"right\", \"double\": false}\n"
    "- type_text: {\"text\": \"texte à saisir\", \"press_enter\": false}\n"
    "- edit_text: {\"command\": \"undo\" | \"redo\" | \"delete_all\" | \"delete_word\" | \"delete_line\" | \"newline\" | \"replace\", \"new_text\": \"...\"}\n"
    "- scroll: {\"direction\": \"down\" | \"up\" | \"top\" | \"bottom\", \"amount\": 6}\n"
    "- search_in_page: {\"query\": \"mot recherché\"}\n"
    "- press_hotkey: {\"keys\": \"enter\"|\"escape\"|\"ctrl+s\"|\"ctrl+c\"|\"ctrl+v\"|\"ctrl+a\"|\"ctrl+t\"|\"ctrl+w\"|\"alt+f4\"|\"win+d\"}\n"
    "- empty_recycle_bin: {}\n"
    "- set_volume: {\"level\": 0-100}\n"
    "- media_control: {\"command\": \"play_pause\"|\"next\"|\"prev\"}\n"
    "- create_file: {\"filename\": \"nom.txt\", \"content\": \"texte\", \"folder\": \"desktop\"}\n"
    "- browse_web: {\"query\": \"recherche\", \"site\": \"youtube\"|\"google\"|\"github\"}\n"
    "- take_screenshot: {}\n"
    "- run_powershell: {\"command\": \"code powershell\"}\n\n"
    "2. Si la demande est une simple question d'information, salutation ou explication (ex: 'c\'est quoi un CRM', 'quelle heure est-il', 'bonjour'), réponds DIRECTEMENT en texte clair, naturel et concis (1 à 2 phrases) SANS JSON."
)

def parse_agent_action(llm_output: str) -> Optional[dict]:
    """Parse un bloc d'action JSON retourné par le LLM (Computer Use Agent)."""
    txt = (llm_output or "").strip()
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', txt, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    if txt.startswith('{') and txt.endswith('}'):
        try:
            return json.loads(txt)
        except Exception:
            pass
    m2 = re.search(r'(\{"action":\s*"[^"]+".*?\})', txt, re.DOTALL)
    if m2:
        try:
            return json.loads(m2.group(1))
        except Exception:
            pass
    return None

def query_agnes_ai(user_query: str, messages: Optional[List[dict]] = None, timeout: int = 12, on_chunk: Optional[Callable[[str], None]] = None) -> str:
    """
    Interroge l'API Agnes AI 3.0 Flash avec streaming en direct, support DeepTalk multi-tours et Computer-Use complet.
    Latence moyenne constatée : ~0.8s.
    """
    t0 = time.time()
    headers = {
        "Authorization": f"Bearer {AGNES_API_KEY}",
        "Content-Type": "application/json"
    }

    payload_messages = messages if messages else [
        {"role": "system", "content": COMPUTER_USE_SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]

    payload = {
        "model": "agnes-3.0-flash",
        "messages": payload_messages,
        "stream": True if on_chunk else False,
        "temperature": 0.2,
        "max_tokens": 360
    }

    try:
        req = urllib.request.Request(AGNES_API_URL, json.dumps(payload).encode("utf-8"), headers)
        if on_chunk:
            accumulated = []
            is_json_mode = False
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for line in resp:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: ") and not line_str.endswith("[DONE]"):
                        try:
                            chunk = json.loads(line_str[6:])
                            delta = chunk["choices"][0].get("delta", {})
                            d_text = delta.get("content") or ""
                            if d_text:
                                accumulated.append(d_text)
                                joined = "".join(accumulated).lstrip()
                                if joined.startswith("{") or joined.startswith("`"):
                                    is_json_mode = True
                                elif not is_json_mode:
                                    on_chunk(d_text)
                        except Exception:
                            pass
            full_text = "".join(accumulated).strip()
            print(f"[Brain Agnes - 3.0 Flash] Réponse streamée en {time.time() - t0:.2f}s : '{full_text}'")
            return full_text
        else:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choice = data["choices"][0]["message"]
                ans = choice.get("content") or ""
                print(f"[Brain Agnes - 3.0 Flash] Réponse générée en {time.time() - t0:.2f}s : '{ans}'")
                return ans
    except Exception as e:
        print(f"[Brain Agnes] Erreur appel API : {e}")
        return ""

def query_nvidia_nim(user_query: str, messages: Optional[List[dict]] = None, model_name: Optional[str] = None, timeout: int = 15, on_chunk: Optional[Callable[[str], None]] = None) -> str:
    """
    Interroge l'API NVIDIA NIM avec le mode Computer-Use Agent complet et support DeepTalk multi-tours.
    Supporte les 5 modèles benchmarkés et le streaming intelligent.
    """
    t0 = time.time()
    headers = {
        "Authorization": f"Bearer {NIM_API_KEY}",
        "Content-Type": "application/json"
    }

    selected_model = model_name or get_current_nim_model()

    payload_messages = messages if messages else [
        {"role": "system", "content": COMPUTER_USE_SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]

    payload = {
        "model": selected_model,
        "messages": payload_messages,
        "stream": True if on_chunk else False,
        "temperature": 0.2,
        "max_tokens": 380
    }

    try:
        req = urllib.request.Request(NIM_API_URL, json.dumps(payload).encode("utf-8"), headers)
        if on_chunk:
            accumulated = []
            is_json_mode = False
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for line in resp:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: ") and not line_str.endswith("[DONE]"):
                        try:
                            chunk = json.loads(line_str[6:])
                            delta = chunk["choices"][0].get("delta", {})
                            d_text = delta.get("content") or delta.get("reasoning_content") or ""
                            if d_text:
                                accumulated.append(d_text)
                                joined = "".join(accumulated).lstrip()
                                # Si le texte commence par '{' ou '```', on est en mode commande JSON
                                if joined.startswith("{") or joined.startswith("`"):
                                    is_json_mode = True
                                elif not is_json_mode:
                                    on_chunk(d_text)
                        except Exception:
                            pass
            full_text = "".join(accumulated).strip()
            full_text = re.sub(r'<think>.*?</think>', '', full_text, flags=re.DOTALL).strip()
            print(f"[Brain NIM - {selected_model}] Réponse streamée en {time.time() - t0:.2f}s : '{full_text}'")
            return full_text
        else:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choice = data["choices"][0]["message"]
                ans = choice.get("content") or choice.get("reasoning_content") or ""
                ans = re.sub(r'<think>.*?</think>', '', ans, flags=re.DOTALL).strip()
                print(f"[Brain NIM - {selected_model}] Réponse générée en {time.time() - t0:.2f}s : '{ans}'")
                return ans
    except Exception as e:
        print(f"[Brain NIM - {selected_model}] Erreur appel API : {e}")
        return ""

def query_agy_llm(user_query: str, timeout: int = 30, on_chunk: Optional[Callable[[str], None]] = None) -> str:
    """
    Interroge le démon local agy via ACP avec streaming live.
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
    Moteur conversationnel et d'action ultra-rapide (<0.01s local, ~0.35s via NVIDIA NIM, fallback ACP).
    """
    if not query or not query.strip():
        return "Je ne vous ai pas bien entendu. Maintenez Win + Alt et parlez."

    q = query.lower().strip()

    # 0. Commande de réinitialisation de la mémoire conversationnelle persistante DeepTalk
    if any(w in q for w in [
        "oublie la discussion", "oublie notre discussion", "oublie notre conversation",
        "nouvelle discussion", "nouvelle conversation", "repartons de zéro",
        "recommençons à zéro", "efface la mémoire", "reset mémoire"
    ]):
        try:
            from island.deeptalk import DeepTalk
            DeepTalk.get_instance().clear()
            return "Mémoire conversationnelle DeepTalk réinitialisée. De quoi souhaitez-vous parler ?"
        except Exception:
            return "Discussion réinitialisée."

    # 1. Calculs mathématiques instantanés (0.001s)
    math_res = solve_instant_math(q)
    if math_res:
        try:
            from island.deeptalk import DeepTalk
            DeepTalk.get_instance().record_turn(query, math_res)
        except Exception:
            pass
        return math_res

    # 2. Salutations rapides (0.001s)
    if any(w in q for w in ["bonjour", "salut", "coucou", "hello", "bonsoir"]) and len(q.split()) <= 4:
        greetings = [
            "Bonjour ! Je suis Antigravity, à vos côtés.",
            "Salut ! Prêt pour vos requêtes.",
            "Bonjour ! Que puis-je faire pour vous ?"
        ]
        chosen = random.choice(greetings)
        try:
            from island.deeptalk import DeepTalk
            DeepTalk.get_instance().record_turn(query, chosen)
        except Exception:
            pass
        return chosen

    # 3. Heure exacte locale (0.001s)
    if any(w in q for w in ["heure", "quelle heure"]):
        now = datetime.datetime.now()
        ans = f"Il est actuellement {now.strftime('%Hh%M')}."
        try:
            from island.deeptalk import DeepTalk
            DeepTalk.get_instance().record_turn(query, ans)
        except Exception:
            pass
        return ans

    # 4. Date exacte locale (0.001s)
    if any(w in q for w in ["date", "quel jour", "aujourd'hui"]):
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        now = datetime.datetime.now()
        ans = f"Nous sommes le {jours[now.weekday()]} {now.day} {mois[now.month - 1]} {now.year}."
        try:
            from island.deeptalk import DeepTalk
            DeepTalk.get_instance().record_turn(query, ans)
        except Exception:
            pass
        return ans

    # 5. Identité & Capacité (0.001s)
    if any(w in q for w in ["qui es-tu", "qui es tu", "c'est quoi cette encoche", "t'es qui"]):
        ans = "Je suis Antigravity Island : votre Dynamic Island intelligente sur Windows avec mémoire persistante DeepTalk."
        try:
            from island.deeptalk import DeepTalk
            DeepTalk.get_instance().record_turn(query, ans)
        except Exception:
            pass
        return ans

    if any(w in q for w in ["que sais-tu faire", "que peux-tu faire", "aide-moi", "fonctionnalités"]):
        ans = "Je contrôle votre PC (ouvrir, écrire, cliquer), surveille vos notifications et mémorise nos échanges avec DeepTalk."
        try:
            from island.deeptalk import DeepTalk
            DeepTalk.get_instance().record_turn(query, ans)
        except Exception:
            pass
        return ans

    # 6. État / Forme (0.001s)
    if any(w in q for w in ["comment vas-tu", "comment ca va", "ca va", "ça va", "tu vas bien"]) and len(q.split()) <= 4:
        ans = "Je fonctionne parfaitement ! Prêt pour vos requêtes."
        try:
            from island.deeptalk import DeepTalk
            DeepTalk.get_instance().record_turn(query, ans)
        except Exception:
            pass
        return ans

    # 7. Blague rapide (0.001s)
    if any(w in q for w in ["blague", "rigoler", "drôle", "humour"]):
        jokes = [
            "Que dit une imprimante qui tombe dans l'eau ? J'ai papier !",
            "Pourquoi les développeurs détestent la nature ? Il y a trop de bugs !",
            "Que fait un geek quand il a froid ? Il se met près du pare-feu !"
        ]
        chosen = random.choice(jokes)
        try:
            from island.deeptalk import DeepTalk
            DeepTalk.get_instance().record_turn(query, chosen)
        except Exception:
            pass
        return chosen

    # 8. Contrôle et Automatisation Desktop (Action immédiate en <0.02s)
    desktop_res = DesktopController.execute_intent(query)
    if desktop_res:
        success, msg = desktop_res
        try:
            from island.deeptalk import DeepTalk
            DeepTalk.get_instance().record_turn(query, msg)
        except Exception:
            pass
        return msg

    # 8.1 Boucle Récursive Harness² (Propose-Probe-Compose) & Mémoire RAG Fichiers (<0.01s)
    try:
        from island.harness.engine import HarnessEngine
        harness_res = HarnessEngine.get_instance().execute_recursive(query)
        if harness_res:
            success, msg = harness_res
            try:
                from island.deeptalk import DeepTalk
                DeepTalk.get_instance().record_turn(query, msg)
            except Exception:
                pass
            return msg
    except Exception as e:
        print(f"[Brain Harness²] Exception : {e}")

    # 9. Vision et Lecture de l'écran / Diagramme / Schéma
    is_vision_query = any(w in q for w in [
        "à l'écran", "a l'ecran", "mon écran", "mon ecran", "ce qui est affiché",
        "regarde l'écran", "regarde l'ecran", "que vois-tu", "qu'est-ce qu'il y a",
        "lis ce qui", "décris l'écran", "decris l'ecran", "décris ce que tu vois",
        "decris ce que tu vois", "diagramme", "schéma", "schema", "analyse l'écran",
        "analyse l'ecran", "qu'est-ce que tu vois", "décris", "decris"
    ])
    if is_vision_query:
        vis_res = query_vision_model(query, on_chunk=on_chunk)
        if vis_res:
            try:
                from island.deeptalk import DeepTalk
                DeepTalk.get_instance().record_turn(query, vis_res)
            except Exception:
                pass
            return vis_res

    # 10. Moteur LLM sélectionné (Agnes AI 3.0 Flash par défaut, NVIDIA NIM ou Antigravity CLI ACP)
    provider = get_current_provider()
    print(f"[Brain] Fournisseur LLM actif : {provider.upper()}")

    # Injection du contexte et des leçons Harness²
    harness_context = ""
    try:
        from island.harness.engine import HarnessEngine
        harness_context = HarnessEngine.get_instance().get_context_lessons(query)
    except Exception:
        pass

    effective_query = f"{harness_context}\n\n{query}" if harness_context else query

    # Préparation du contexte multi-tours DeepTalk
    multi_turn_messages = None
    system_prompt_with_harness = f"{COMPUTER_USE_SYSTEM_PROMPT}\n\n{harness_context}" if harness_context else COMPUTER_USE_SYSTEM_PROMPT
    try:
        from island.deeptalk import DeepTalk
        multi_turn_messages = DeepTalk.get_instance().get_messages_for_llm(
            current_query=query,
            system_prompt=system_prompt_with_harness
        )
    except Exception as e:
        print(f"[Brain DeepTalk] Erreur chargement contexte : {e}")

    # Pour ACP CLI ou contextes texte brut
    conversation_summary = ""
    try:
        from island.deeptalk import DeepTalk
        conversation_summary = DeepTalk.get_instance().get_context_summary_text(limit_turns=3)
    except Exception:
        pass

    effective_text_query = f"{conversation_summary}\n\n{effective_query}" if conversation_summary else effective_query

    raw_resp = ""
    if provider == "agnes":
        raw_resp = query_agnes_ai(effective_query, messages=multi_turn_messages, timeout=12, on_chunk=on_chunk)
        if not raw_resp:
            print("[Brain] Repli sur NVIDIA NIM...")
            raw_resp = query_nvidia_nim(effective_query, messages=multi_turn_messages, timeout=15, on_chunk=on_chunk)
    elif provider == "nim":
        raw_resp = query_nvidia_nim(effective_query, messages=multi_turn_messages, timeout=15, on_chunk=on_chunk)
        if not raw_resp:
            print("[Brain] Repli sur Agnes AI...")
            raw_resp = query_agnes_ai(effective_query, messages=multi_turn_messages, timeout=12, on_chunk=on_chunk)
    else:
        raw_resp = query_agy_llm(effective_text_query, timeout=25, on_chunk=on_chunk)
        if not raw_resp:
            print("[Brain] Repli sur Agnes AI...")
            raw_resp = query_agnes_ai(effective_query, messages=multi_turn_messages, timeout=12, on_chunk=on_chunk)

    if raw_resp:
        final_answer = raw_resp
        # Vérification si le LLM a déclenché une action d'agent Computer-Use
        agent_call = parse_agent_action(raw_resp)
        if agent_call and "action" in agent_call:
            act_name = agent_call["action"]
            act_params = agent_call.get("params", {})
            say_msg = agent_call.get("say", "")
            print(f"[Brain Agent Action] Action déclenchée par LLM : {act_name} avec {act_params}")
            success, res_msg = DesktopController.execute_action(act_name, act_params)

            # Auto-évolution Harness² : consigner l'expérience
            if success:
                try:
                    from island.harness.engine import HarnessEngine
                    HarnessEngine.get_instance().library.record_experience(
                        cue=query,
                        lesson=f"Exécuté avec succès via {act_name} : {act_params}",
                        evidence=res_msg,
                        domain="agent_actions",
                        task_id=f"action_{int(time.time())}"
                    )
                except Exception:
                    pass

            if say_msg:
                final_answer = say_msg if success else f"{say_msg} ({res_msg})"
            else:
                final_answer = res_msg

        # Enregistrement dans DeepTalk
        try:
            from island.deeptalk import DeepTalk
            DeepTalk.get_instance().record_turn(query, final_answer)
        except Exception as e:
            print(f"[Brain DeepTalk] Erreur record_turn : {e}")

        return final_answer

    fallback_msg = f"Bien reçu : « {query} ». Je reste à vos côtés."
    try:
        from island.deeptalk import DeepTalk
        DeepTalk.get_instance().record_turn(query, fallback_msg)
    except Exception:
        pass
    return fallback_msg
