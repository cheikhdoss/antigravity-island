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
from island.agy_knowledge import AgyKnowledge

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
    """Lit le fournisseur configuré dans settings.json ('agnes', 'nim', 'gemini', 'agy'). Par défaut: agnes."""
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

def get_gemini_api_key() -> str:
    """Lit la clé API Google Gemini configurée dans settings.json ou l'environnement."""
    try:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        settings_path = os.path.join(appdata, "AntigravityIsland", "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                k = data.get("gemini_api_key", "").strip()
                if k:
                    return k
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")

def get_unified_system_prompt(is_vision: bool = False) -> str:
    """Génère le prompt d'intelligence, savoir et compétences unifié pour TOUS les modèles (NVIDIA NIM, Agnes, Gemini, AGY)."""
    base_prompt = AgyKnowledge.build_system_prompt(is_vision=is_vision)
    runtime_ctx = AgyKnowledge.get_runtime_context()
    return f"{base_prompt}\n\n{runtime_ctx}"

COMPUTER_USE_SYSTEM_PROMPT = AgyKnowledge.build_system_prompt(is_vision=False)

def query_gemini_api(prompt: str, image_b64: Optional[str] = None, mime_type: str = "image/jpeg", system_prompt: str = "", on_chunk: Optional[Callable[[str], None]] = None) -> str:
    """
    Appelle Google DeepMind Gemini 2.5 Flash / 2.0 Flash directement via l'API REST officielle Google.
    Latence sub-seconde (<0.9s), support natif texte et vision multimodale.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        print("[Brain Gemini] Clé API Gemini manquante dans settings.json.")
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    parts = []
    if image_b64:
        raw_b64 = image_b64.split(",", 1)[1] if "," in image_b64 else image_b64
        parts.append({
            "inlineData": {
                "mimeType": mime_type,
                "data": raw_b64
            }
        })
    parts.append({"text": prompt})

    req_body = {
        "contents": [
            {
                "role": "user",
                "parts": parts
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 350
        }
    }
    sys_instruction = system_prompt if system_prompt else get_unified_system_prompt(is_vision=bool(image_b64))
    req_body["systemInstruction"] = {
        "parts": [{"text": sys_instruction}]
    }

    headers = {"Content-Type": "application/json"}
    try:
        t0 = time.time()
        req = urllib.request.Request(url, json.dumps(req_body).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                content_parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in content_parts).strip()
                text = re.sub(r'\*+', '', text)
                text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
                text = re.sub(r'`', '', text).strip()
                print(f"[Brain Gemini 2.5 Flash] Réponse en {time.time() - t0:.2f}s : '{text}'")
                if on_chunk and text:
                    try:
                        on_chunk(text)
                    except Exception:
                        pass
                return text
    except Exception as e:
        print(f"[Brain Gemini] Erreur appel Gemini Direct : {e}")
    return ""

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

        try:
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            latest = os.path.join(appdata, "AntigravityIsland", "screenshots", "screen_latest.png")
            if os.path.exists(latest):
                from PIL import Image
                with Image.open(latest) as img:
                    img.thumbnail((1280, 720))
                    buf = io.BytesIO()
                    img.convert("RGB").save(buf, format="JPEG", quality=80)
                    b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
                    return f"data:image/jpeg;base64,{b64_data}"
        except Exception as e3:
            print("[Brain Vision] Erreur capture fallback fichier:", e3)
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

    system_prompt = get_unified_system_prompt(is_vision=True)

    # Récupération de l'historique conversationnel récent DeepTalk pour contexte multi-tours
    prev_turns = []
    try:
        from island.deeptalk import DeepTalk
        dt = DeepTalk.get_instance()
        with dt._lock:
            for m in dt.history[-6:]:
                prev_turns.append({"role": m["role"], "content": m["content"]})
    except Exception:
        pass

    if v_prov == "gemini_vl":
        # 1. Google DeepMind Gemini 2.5 Flash Vision (<0.9s - Multimodal Direct)
        ans = query_gemini_api(prompt, image_b64=data_url, system_prompt=system_prompt, on_chunk=on_chunk)
        if ans:
            print(f"[Brain Vision Gemini 2.5 Flash] Réponse en {time.time() - t0:.2f}s : '{ans}'")
            return ans
        print("[Brain Vision Gemini] Clé absente ou échec API, bascule rapide sur Agnes AI...")

    elif v_prov == "agy_vl":
        # 2. Antigravity CLI ACP Vision (Local ~7s)
        raw_b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
        daemon = AgyDaemon.get_instance()
        ans = daemon.ask_vision(prompt, image_b64=raw_b64, timeout=30.0, on_chunk=on_chunk)
        if ans:
            print(f"[Brain Vision AGY ACP] Réponse en {time.time() - t0:.2f}s : '{ans}'")
            return ans
        print("[Brain Vision AGY ACP] Échec ou timeout, bascule rapide sur Agnes AI...")

    if v_prov in ["agnes", "gemini_vl", "agy_vl"]:
        # 3. Agnes AI 3.0 Flash Vision (~1.0s - Par défaut et repli ultra-rapide)
        headers = {
            "Authorization": f"Bearer {AGNES_API_KEY}",
            "Content-Type": "application/json"
        }
        vision_messages = [{"role": "system", "content": system_prompt}]
        vision_messages.extend(prev_turns)
        vision_messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]
        })
        payload = {
            "model": "agnes-3.0-flash",
            "messages": vision_messages,
            "max_tokens": 350,
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

    # 4. NVIDIA Nemotron 3.5 Super-VL 120B
    headers = {
        "Authorization": f"Bearer {NIM_API_KEY}",
        "Content-Type": "application/json"
    }
    vision_messages = [{"role": "system", "content": system_prompt}]
    vision_messages.extend(prev_turns)
    vision_messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}}
        ]
    })
    payload = {
        "model": "nvidia/nemotron-3.5-super-vl-120b-a12b",
        "messages": vision_messages,
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
        {"role": "system", "content": get_unified_system_prompt(is_vision=False)},
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
        {"role": "system", "content": get_unified_system_prompt(is_vision=False)},
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

def query_agy_llm(user_query: str, timeout: int = 30, on_chunk: Optional[Callable[[str], None]] = None, conversation_history: str = "") -> str:
    """
    Interroge le démon local agy via ACP avec streaming live, intelligence supérieure, savoir et compétences.
    """
    daemon = AgyDaemon.get_instance()
    try:
        t0 = time.time()
        resp = daemon.ask(user_query, on_chunk=on_chunk, timeout=timeout, conversation_history=conversation_history)
        if resp:
            print(f"[Brain AGY] Réponse ACP d'élite générée en {time.time() - t0:.2f}s : '{resp}'")
            return resp
    except Exception as e:
        print(f"[Brain AGY] Erreur démon : {e}")

    return ""

def record_turn_all_memories(query: str, response: str, event_type: str = "chat", action: Optional[dict] = None):
    """Consigne l'échange dans la session vivante d'Island et dans la mémoire persistante DeepTalk."""
    try:
        from island.session_manager import IslandSessionManager
        IslandSessionManager.get_instance().record_turn(query, response, event_type=event_type, action=action)
    except Exception as e:
        print(f"[Brain] Erreur consignation session : {e}")

    try:
        from island.deeptalk import DeepTalk
        DeepTalk.get_instance().record_turn(query, response)
    except Exception as e:
        print(f"[Brain] Erreur consignation DeepTalk : {e}")

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

    # 0.1 Demande de récapitulatif / jonctions de la session vivante (depuis le démarrage d'Island)
    if any(w in q for w in [
        "résume la session", "resume la session", "récapitule la session", "recapitule la session",
        "qu'est-ce qu'on a fait", "qu est ce qu on a fait", "qu'avons-nous fait", "ce qu'on a fait",
        "depuis le démarrage", "depuis le demarrage", "historique de la session", "bilan de la session"
    ]):
        try:
            from island.session_manager import IslandSessionManager
            ans = IslandSessionManager.get_instance().get_session_summary_answer()
            record_turn_all_memories(query, ans, event_type="system")
            return ans
        except Exception:
            pass

    # 1. Calculs mathématiques instantanés (0.001s)
    math_res = solve_instant_math(q)
    if math_res:
        record_turn_all_memories(query, math_res, event_type="math")
        return math_res

    # 2. Salutations rapides (0.001s)
    if any(w in q for w in ["bonjour", "salut", "coucou", "hello", "bonsoir"]) and len(q.split()) <= 4:
        greetings = [
            "Bonjour ! Je suis Antigravity, à vos côtés.",
            "Salut ! Prêt pour vos requêtes.",
            "Bonjour ! Que puis-je faire pour vous ?"
        ]
        chosen = random.choice(greetings)
        record_turn_all_memories(query, chosen, event_type="chat")
        return chosen

    # 3. Heure exacte locale (0.001s)
    if any(w in q for w in ["heure", "quelle heure"]):
        now = datetime.datetime.now()
        ans = f"Il est actuellement {now.strftime('%Hh%M')}."
        record_turn_all_memories(query, ans, event_type="chat")
        return ans

    # 4. Date exacte locale (0.001s)
    if any(w in q for w in ["date", "quel jour", "aujourd'hui"]):
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        now = datetime.datetime.now()
        ans = f"Nous sommes le {jours[now.weekday()]} {now.day} {mois[now.month - 1]} {now.year}."
        record_turn_all_memories(query, ans, event_type="chat")
        return ans

    # 5. Identité & Capacité (0.001s)
    if any(w in q for w in ["qui es-tu", "qui es tu", "c'est quoi cette encoche", "t'es qui"]):
        ans = "Je suis Antigravity Island : votre Dynamic Island intelligente sur Windows avec mémoire persistante DeepTalk et session vivante."
        record_turn_all_memories(query, ans, event_type="chat")
        return ans

    if any(w in q for w in ["que sais-tu faire", "que peux-tu faire", "aide-moi", "fonctionnalités"]):
        ans = "Je contrôle votre PC (ouvrir, écrire, cliquer), surveille vos notifications et mémorise nos échanges avec DeepTalk et le gestionnaire de session."
        record_turn_all_memories(query, ans, event_type="chat")
        return ans

    # 6. État / Forme (0.001s)
    if any(w in q for w in ["comment vas-tu", "comment ca va", "ca va", "ça va", "tu vas bien"]) and len(q.split()) <= 4:
        ans = "Je fonctionne parfaitement ! Prêt pour vos requêtes."
        record_turn_all_memories(query, ans, event_type="chat")
        return ans

    # 7. Blague rapide (0.001s)
    if any(w in q for w in ["blague", "rigoler", "drôle", "humour"]):
        jokes = [
            "Que dit une imprimante qui tombe dans l'eau ? J'ai papier !",
            "Pourquoi les développeurs détestent la nature ? Il y a trop de bugs !",
            "Que fait un geek quand il a froid ? Il se met près du pare-feu !"
        ]
        chosen = random.choice(jokes)
        record_turn_all_memories(query, chosen, event_type="chat")
        return chosen

    # 8. Contrôle et Automatisation Desktop (Action immédiate en <0.02s)
    desktop_res = DesktopController.execute_intent(query)
    if desktop_res:
        success, msg = desktop_res
        record_turn_all_memories(query, msg, event_type="action", action={"intent": query, "result": msg})
        return msg

    # 8.1 Boucle Récursive Harness² (Propose-Probe-Compose) & Mémoire RAG Fichiers (<0.01s)
    try:
        from island.harness.engine import HarnessEngine
        harness_res = HarnessEngine.get_instance().execute_recursive(query)
        if harness_res:
            success, msg = harness_res
            record_turn_all_memories(query, msg, event_type="harness")
            return msg
    except Exception as e:
        print(f"[Brain Harness²] Exception : {e}")

    # 9. Vision et Lecture de l'écran / Diagramme / Schéma
    def is_visual_inspection_query(text: str) -> bool:
        import unicodedata
        t_norm = unicodedata.normalize('NFD', text.lower())
        norm = ''.join(c for c in t_norm if unicodedata.category(c) != 'Mn')
        norm = re.sub(r'[\'’\-]', ' ', norm)
        norm = ' '.join(norm.split())

        if any(m in norm for m in ['quel est le modele', 'quel modele', 'quelle est le model', 'quel est le model', 'modele de vision', 'model de vision']):
            return False

        has_screen = any(w in norm for w in ['ecran', 'screen'])
        has_visual = any(w in norm for w in [
            'voi', 'voit', 'vois', 'regard', 'affich', 'pass', 'montr', 'lis', 'lit',
            'decri', 'analys', 'expliqu', 'qu est ce', 'c est quoi', 'ouvert'
        ])
        if has_screen and has_visual:
            return True

        direct_patterns = [
            'que vois tu', 'que voit tu', 'tu vois quoi', 'tu voit quoi',
            'qu est ce que tu vois', 'qu est ce que tu voit', 'ce que tu vois', 'ce que tu voit',
            'ce qui se passe', 'ce qui ce passe', 'diagramme', 'schema',
            'qu est ce qu il y a', 'qu est ce qui est ecrit', 'qu est ce qui est affiche',
            'qui est affiche', 'ce qui est affiche', 'decris l ecran', 'decris mon ecran',
            'decris ce que tu vois', 'decris ce que tu voit', 'analyse l ecran', 'analyse mon ecran'
        ]
        if any(p in norm for p in direct_patterns):
            return True

        # Suivi contextuel : si la conversation récente parlait de l'écran/QCM et que la requête demande une réponse/choix
        try:
            from island.deeptalk import DeepTalk
            dt = DeepTalk.get_instance()
            with dt._lock:
                if dt.history:
                    last_msg = dt.history[-1]["content"].lower()
                    last_user = dt.history[-2]["content"].lower() if len(dt.history) >= 2 else ""
                    was_about_screen = any(w in last_msg or w in last_user for w in ["écran", "ecran", "qcm", "capture", "aws", "fenêtre", "navigateur", "affiche"])
                    if was_about_screen:
                        is_followup_answer = any(w in norm for w in [
                            "reponse", "bonne reponse", "choisir", "aide moi a choisir", "aide moi",
                            "laquelle", "lequel", "quelle option", "option a", "option b", "option c",
                            "choix", "exercice", "question"
                        ])
                        if is_followup_answer:
                            print("[Brain Vision] Suivi contextuel activé : la question précédente portait sur l'écran.")
                            return True
        except Exception:
            pass

        return False

    is_vision_query = is_visual_inspection_query(query)
    if is_vision_query:
        vis_res = query_vision_model(query, on_chunk=on_chunk)
        if vis_res:
            record_turn_all_memories(query, vis_res, event_type="vision")
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

    # Injection du contexte de Session vivante et des Jonctions Contextuelles
    session_junction_prompt = ""
    try:
        from island.session_manager import IslandSessionManager
        session_junction_prompt = IslandSessionManager.get_instance().get_junction_prompt(query)
    except Exception as e:
        print(f"[Brain Session Junction] Erreur génération jonction : {e}")

    effective_query = f"{harness_context}\n\n{query}" if harness_context else query

    # Préparation du prompt système enrichi (Savoirs, Harness² et Jonctions de session)
    unified_prompt = get_unified_system_prompt(is_vision=False)
    system_parts = [unified_prompt]
    if harness_context:
        system_parts.append(harness_context)
    if session_junction_prompt:
        system_parts.append(session_junction_prompt)
    system_prompt_with_context = "\n\n".join(system_parts)

    # Préparation du contexte multi-tours pour les API de complétion
    multi_turn_messages = None
    try:
        from island.deeptalk import DeepTalk
        multi_turn_messages = DeepTalk.get_instance().get_messages_for_llm(
            current_query=query,
            system_prompt=system_prompt_with_context
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

    full_context_blocks = []
    if session_junction_prompt:
        full_context_blocks.append(session_junction_prompt)
    if conversation_summary:
        full_context_blocks.append(conversation_summary)
    full_context_blocks.append(effective_query)
    effective_text_query = "\n\n".join(full_context_blocks)

    raw_resp = ""
    if provider == "gemini":
        raw_resp = query_gemini_api(effective_text_query, system_prompt=system_prompt_with_context, on_chunk=on_chunk)
        if not raw_resp:
            print("[Brain] Repli sur Agnes AI...")
            raw_resp = query_agnes_ai(effective_query, messages=multi_turn_messages, timeout=12, on_chunk=on_chunk)
    elif provider == "agnes":
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
        raw_resp = query_agy_llm(effective_query, timeout=35, on_chunk=on_chunk, conversation_history=effective_text_query)
        if not raw_resp:
            print("[Brain] Repli sur Agnes AI...")
            raw_resp = query_agnes_ai(effective_query, messages=multi_turn_messages, timeout=12, on_chunk=on_chunk)

    if raw_resp:
        final_answer = raw_resp
        action_recorded = None
        # Vérification si le LLM a déclenché une action d'agent Computer-Use
        agent_call = parse_agent_action(raw_resp)
        if agent_call and "action" in agent_call:
            act_name = agent_call["action"]
            act_params = agent_call.get("params", {})
            say_msg = agent_call.get("say", "")
            action_recorded = {"action": act_name, "params": act_params}
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

        # Enregistrement synchronisé dans la Session active et dans DeepTalk
        record_turn_all_memories(
            query=query,
            response=final_answer,
            event_type="action" if action_recorded else "chat",
            action=action_recorded
        )

        return final_answer

    fallback_msg = f"Bien reçu : « {query} ». Je reste à vos côtés."
    record_turn_all_memories(query, fallback_msg, event_type="fallback")
    return fallback_msg
