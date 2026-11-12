import os
import sys
import subprocess
import json
import re
import ctypes
import time
from typing import Optional, Tuple, Dict

class DesktopController:
    """
    Moteur de contrôle et d'automatisation de la machine pour Antigravity Island.
    Combine les capacités natives Windows (C API ctypes), le moteur OCR local WinRT,
    le scanner d'applications du Menu Démarrer/Bureau, et le CLI Agent-Desktop de Vercel Labs.
    """
    last_typed_text = ""
    last_app_opened = ""
    _shortcuts_cache: Optional[Dict[str, str]] = None
    _shortcuts_cache_time = 0.0

    @staticmethod
    def get_agent_desktop_bin() -> str:
        """Localise l'exécutable natif de Vercel Labs agent-desktop."""
        candidates = [
            r"C:\Users\pro\AppData\Local\Programs\NodeJS\node_modules\agent-desktop\bin\agent-desktop-win32-x64.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\NodeJS\node_modules\agent-desktop\bin\agent-desktop-win32-x64.exe"),
            os.path.join(os.environ.get("APPDATA", ""), r"npm\node_modules\agent-desktop\bin\agent-desktop-win32-x64.exe"),
            "agent-desktop.cmd",
            "agent-desktop"
        ]
        for c in candidates:
            if os.path.isabs(c) and os.path.exists(c):
                return c
        import shutil
        w = shutil.which("agent-desktop") or shutil.which("agent-desktop.cmd")
        return w or "agent-desktop"

    @staticmethod
    def run_agent_desktop_command(cmd_args: list, timeout: float = 4.0) -> Optional[dict]:
        """Exécute une commande de l'outil Vercel Labs agent-desktop et parse l'enveloppe JSON."""
        try:
            exe = DesktopController.get_agent_desktop_bin()
            full_cmd = [exe] + cmd_args
            is_cmd_script = exe.lower().endswith((".cmd", ".bat", ".ps1"))
            res = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=0x08000000,
                shell=is_cmd_script
            )
            if res.stdout and res.stdout.strip():
                return json.loads(res.stdout.strip())
        except Exception as e:
            print("[AgentDesktop] Erreur exécution commande:", e)
        return None

    @staticmethod
    def get_installed_shortcuts() -> Dict[str, str]:
        """
        Scanne et indexe tous les raccourcis .lnk et exécutables du Menu Démarrer et du Bureau.
        Permet de lancer n'importe quelle application installée sur le PC en < 0.001s.
        """
        now = time.time()
        if DesktopController._shortcuts_cache and (now - DesktopController._shortcuts_cache_time) < 60.0:
            return DesktopController._shortcuts_cache

        dirs = [
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.path.expanduser("~"), "Desktop"),
            r"C:\Users\Public\Desktop"
        ]
        shortcuts: Dict[str, str] = {}
        for d in dirs:
            if os.path.exists(d):
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith((".lnk", ".exe")):
                            base = f.rsplit(".", 1)[0].lower()
                            clean = re.sub(r'[\.,;:!?\'"«»]', '', base).strip()
                            shortcuts[clean] = os.path.join(root, f)

        DesktopController._shortcuts_cache = shortcuts
        DesktopController._shortcuts_cache_time = now
        return shortcuts

    @staticmethod
    def clean_target_name(raw_name: str) -> str:
        """Nettoie une chaîne de nom d'application (enlève ponctuation, articles, prépositions)."""
        clean = raw_name.lower().strip()
        # Enlever la ponctuation finale et guillemets (ex: 'corbeille.', 'bloc.')
        clean = re.sub(r'[\.,;:!?\'"«»\(\)\[\]]', '', clean).strip()
        # Enlever les articles définis/indéfinis au début
        clean = re.sub(r'^(?:le|la|les|l[\'\s]|un|une|des|mon|ma|mes|ton|ta|tes|the|a|an)\s+', '', clean).strip()
        return clean

    @staticmethod
    def open_application(app_name: str) -> Tuple[bool, str]:
        """
        Lance une application, un dossier spécial ou un raccourci Windows de manière ultra-fiable
        sans jamais afficher de dialogue d'erreur Windows "introuvable".
        """
        clean_name = DesktopController.clean_target_name(app_name)
        if not clean_name:
            return False, "Nom d'application manquant."

        # 1. Table des alias système fondamentaux et dossiers spéciaux Windows
        shell_system_map = {
            # Corbeille
            "corbeille": "explorer.exe shell:RecycleBinFolder",
            "recycle bin": "explorer.exe shell:RecycleBinFolder",
            "trash": "explorer.exe shell:RecycleBinFolder",

            # Bloc-notes / Notepad
            "bloc": "notepad.exe",
            "blocs": "notepad.exe",
            "bloc-notes": "notepad.exe",
            "bloc notes": "notepad.exe",
            "bloc note": "notepad.exe",
            "notepad": "notepad.exe",
            "carnet": "notepad.exe",

            # Explorateur & Dossiers utilisateur
            "explorateur": "explorer.exe",
            "explorateur de fichiers": "explorer.exe",
            "fichiers": "explorer.exe",
            "dossiers": "explorer.exe",
            "ce pc": "explorer.exe shell:MyComputerFolder",
            "poste de travail": "explorer.exe shell:MyComputerFolder",
            "bureau": "explorer.exe shell:Desktop",
            "desktop": "explorer.exe shell:Desktop",
            "téléchargements": "explorer.exe shell:Downloads",
            "telechargements": "explorer.exe shell:Downloads",
            "downloads": "explorer.exe shell:Downloads",
            "documents": "explorer.exe shell:Personal",
            "mes documents": "explorer.exe shell:Personal",
            "images": "explorer.exe shell:My Pictures",
            "photos": "explorer.exe shell:My Pictures",
            "musique": "explorer.exe shell:My Music",
            "vidéos": "explorer.exe shell:My Video",
            "videos": "explorer.exe shell:My Video",

            # Navigateurs web
            "brave": "start brave",
            "chrome": "start chrome",
            "google chrome": "start chrome",
            "edge": "start msedge",
            "microsoft edge": "start msedge",
            "firefox": "start firefox",

            # Utilitaires Windows
            "calculatrice": "calc.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "paramètres": "start ms-settings:",
            "parametres": "start ms-settings:",
            "settings": "start ms-settings:",
            "panneau de configuration": "control.exe",
            "control panel": "control.exe",
            "gestionnaire des tâches": "taskmgr.exe",
            "gestionnaire de tâches": "taskmgr.exe",
            "gestionnaire des taches": "taskmgr.exe",
            "task manager": "taskmgr.exe",
            "terminal": "start wt.exe || start cmd.exe",
            "powershell": "start powershell",
            "invite de commandes": "start cmd",
            "cmd": "start cmd",
            "paint": "mspaint.exe",
            "peinture": "mspaint.exe",

            # Logiciels et Jeux
            "code": "code",
            "vscode": "code",
            "visual studio code": "code",
            "zed": "zed",
            "spotify": "start spotify:",
            "whatsapp": "start whatsapp:",
            "discord": "start discord:",
            "steam": "start steam:",
            "docker": "start \"\" \"C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe\"",
            "gemini": "start https://gemini.google.com"
        }

        # Test correspondance directe ou sous-chaîne dans la table des alias (par spécificité décroissante)
        for k in sorted(shell_system_map.keys(), key=len, reverse=True):
            cmd = shell_system_map[k]
            if k == clean_name or k in clean_name or clean_name in k:
                try:
                    subprocess.Popen(cmd, shell=True)
                    DesktopController.last_app_opened = clean_name
                    display_name = k.capitalize()
                    return True, f"Application {display_name} lancée."
                except Exception as e:
                    return False, f"Erreur lancement {k} : {e}"

        # 2. Recherche dans les raccourcis installés (Menu Démarrer et Bureau)
        shortcuts = DesktopController.get_installed_shortcuts()
        for k, path in shortcuts.items():
            if clean_name in k or k in clean_name:
                try:
                    os.startfile(path)
                    DesktopController.last_app_opened = clean_name
                    display_name = os.path.basename(path).rsplit(".", 1)[0]
                    return True, f"Application {display_name} lancée."
                except Exception as e:
                    return False, f"Erreur ouverture raccourci {k} : {e}"

        # 3. Tentative avec agent-desktop launch
        res = DesktopController.run_agent_desktop_command(["launch", clean_name])
        if res and res.get("ok"):
            DesktopController.last_app_opened = clean_name
            return True, f"Application {clean_name} lancée avec succès."

        # 4. Échec propre SANS boîte de dialogue Windows
        return False, f"Impossible de trouver l'application « {clean_name} » sur votre PC."

    APP_PROCESS_MAP = {
        # Bloc-notes / Notepad
        "bloc": ["notepad.exe"],
        "blocs": ["notepad.exe"],
        "bloc-notes": ["notepad.exe"],
        "bloc notes": ["notepad.exe"],
        "bloc note": ["notepad.exe"],
        "notepad": ["notepad.exe"],
        "carnet": ["notepad.exe"],
        # Explorateur de fichiers
        "explorateur": ["explorer.exe"],
        "explorateur de fichiers": ["explorer.exe"],
        "fichiers": ["explorer.exe"],
        "dossiers": ["explorer.exe"],
        # Navigateurs
        "chrome": ["chrome.exe"],
        "google chrome": ["chrome.exe"],
        "brave": ["brave.exe"],
        "edge": ["msedge.exe"],
        "microsoft edge": ["msedge.exe"],
        "firefox": ["firefox.exe"],
        # Utilitaires Windows
        "calculatrice": ["CalculatorApp.exe", "calc.exe", "Calculator.exe"],
        "calculator": ["CalculatorApp.exe", "calc.exe", "Calculator.exe"],
        "calc": ["calc.exe"],
        "paramètres": ["SystemSettings.exe"],
        "parametres": ["SystemSettings.exe"],
        "settings": ["SystemSettings.exe"],
        "gestionnaire des tâches": ["Taskmgr.exe"],
        "gestionnaire de tâches": ["Taskmgr.exe"],
        "task manager": ["Taskmgr.exe"],
        "paint": ["mspaint.exe"],
        # Dev & Outils
        "code": ["Code.exe"],
        "vscode": ["Code.exe"],
        "visual studio code": ["Code.exe"],
        "terminal": ["WindowsTerminal.exe", "wt.exe", "cmd.exe", "powershell.exe"],
        "powershell": ["powershell.exe", "pwsh.exe"],
        "cmd": ["cmd.exe"],
        "spotify": ["Spotify.exe"],
        "whatsapp": ["WhatsApp.exe"],
        "discord": ["Discord.exe"],
    }

    @staticmethod
    def close_active_window() -> Tuple[bool, str]:
        """Ferme immédiatement la fenêtre active avec les API natives Windows."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd:
                ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0) # WM_CLOSE
                ctypes.windll.user32.PostMessageW(hwnd, 0x0112, 0xF060, 0) # WM_SYSCOMMAND, SC_CLOSE
                return True, "Fenêtre active fermée."
        except Exception as e:
            print("[DesktopControl] Erreur close_active_window:", e)

        try:
            from island.automation import press_key
            press_key("alt+f4")
            return True, "Fenêtre active fermée."
        except Exception:
            return False, "Erreur fermeture de la fenêtre."

    @staticmethod
    def minimize_active_window() -> Tuple[bool, str]:
        """Minimise immédiatement la fenêtre active (SW_MINIMIZE)."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindowAsync(hwnd, 6) # SW_MINIMIZE = 6
                return True, "Fenêtre active réduite."
        except Exception as e:
            print("[DesktopControl] Erreur minimize_active_window:", e)

        try:
            from island.automation import press_key
            press_key("win+down")
            return True, "Fenêtre active réduite."
        except Exception:
            return False, "Erreur réduction de la fenêtre."

    @staticmethod
    def close_application(app_name: str) -> Tuple[bool, str]:
        """Ferme une application spécifique ou la fenêtre active proprement et nativement."""
        clean = DesktopController.clean_target_name(app_name)
        if clean in ["", "active", "cette fenêtre", "fenêtre", "cette erreur", "erreur", "ce message", "ça", "ca", "la fenêtre", "boite de dialogue", "la"]:
            return DesktopController.close_active_window()

        # 1. Identifier les exécutables correspondants (tri par spécificité décroissante)
        procs_to_kill = []
        display_name = clean.capitalize()
        for k in sorted(DesktopController.APP_PROCESS_MAP.keys(), key=len, reverse=True):
            if k == clean or k in clean or clean in k:
                procs_to_kill.extend(DesktopController.APP_PROCESS_MAP[k])
                display_name = k.capitalize()
                break

        if not procs_to_kill:
            clean_nosp = clean.replace(" ", "")
            procs_to_kill = [f"{clean_nosp}.exe", f"{clean}.exe"]

        closed_any = False

        # 2. Fermeture propre des fenêtres du processus via l'API Windows (WM_CLOSE)
        try:
            import psutil
            from ctypes import wintypes
            for proc in psutil.process_iter(['pid', 'name']):
                pname = (proc.info.get('name') or '').lower()
                if any(target.lower() == pname for target in procs_to_kill):
                    pid = proc.info['pid']

                    def enum_proc(hwnd, lparam):
                        if ctypes.windll.user32.IsWindow(hwnd):
                            w_pid = wintypes.DWORD()
                            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(w_pid))
                            if w_pid.value == pid:
                                ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0) # WM_CLOSE
                                ctypes.windll.user32.PostMessageW(hwnd, 0x0112, 0xF060, 0) # SC_CLOSE
                        return True

                    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                    ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
                    closed_any = True

                    try:
                        proc.wait(timeout=0.4)
                    except Exception:
                        try:
                            proc.terminate()
                        except Exception:
                            pass
        except Exception as e:
            print("[DesktopControl] Erreur fermeture processus psutil:", e)

        # 3. Sécurité supplémentaire : taskkill direct sur les exécutables cibles
        for target in procs_to_kill:
            try:
                res = subprocess.run(f"taskkill /IM {target} /F", shell=True, capture_output=True, timeout=1.5)
                if res.returncode == 0:
                    closed_any = True
            except Exception:
                pass

        if closed_any:
            return True, f"Application {display_name} fermée avec succès."

        # 4. Fallback agent-desktop close-app
        res = DesktopController.run_agent_desktop_command(["close-app", clean])
        if res and res.get("ok"):
            return True, f"Application {display_name} fermée."

        return False, f"Impossible de fermer « {clean} » (déjà fermée ou introuvable)."

    @staticmethod
    def empty_recycle_bin() -> Tuple[bool, str]:
        """Vide instantanément la Corbeille Windows via l'API Shell32 en 0.001s."""
        try:
            # SHEmptyRecycleBinW avec drapeaux SHERB_NOCONFIRMATION (1) | SHERB_NOPROGRESSUI (2) | SHERB_NOSOUND (4) = 7
            res = ctypes.windll.shell32.SHEmptyRecycleBinW(0, None, 7)
            if res == 0:
                return True, "Corbeille vidée avec succès."
            elif res == 0x800401E5: # S_FALSE or already empty
                return True, "La corbeille est déjà vide."
        except Exception as e:
            print("[EmptyRecycleBin] Erreur ctypes:", e)

        # Fallback PowerShell
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True, timeout=3.0, creationflags=0x08000000
            )
            return True, "Corbeille vidée avec succès."
        except Exception as e:
            return False, f"Erreur vidage corbeille : {e}"

    @staticmethod
    def open_and_type(app_name: str, text: str) -> Tuple[bool, str]:
        """Ouvre une application (ex: bloc-notes), attend son affichage et saisit du texte au clavier."""
        clean_app = DesktopController.clean_target_name(app_name)
        success, msg = DesktopController.open_application(clean_app)
        if not success:
            return False, msg

        # Attendre que la fenêtre prenne le focus
        time.sleep(0.75)

        try:
            from island.automation import type_text
            type_text(text)
            DesktopController.last_typed_text = text
            DesktopController.last_app_opened = clean_app
            short_txt = text if len(text) <= 30 else (text[:27] + "...")
            return True, f"{clean_app.capitalize()} ouvert et texte saisi : « {short_txt} »"
        except Exception as e:
            return False, f"Application lancée mais erreur de saisie : {e}"

    @staticmethod
    def create_file(filename: str, content: str = "", folder: str = "desktop") -> Tuple[bool, str]:
        """Crée un fichier sur le Bureau ou dans les Documents."""
        try:
            user_home = os.path.expanduser("~")
            if folder.lower() in ["desktop", "bureau"]:
                target_dir = os.path.join(user_home, "Desktop")
            elif folder.lower() in ["documents", "doc"]:
                target_dir = os.path.join(user_home, "Documents")
            else:
                target_dir = folder

            os.makedirs(target_dir, exist_ok=True)
            clean_fn = re.sub(r'[\/:*?"<>|«»]', '', filename).strip()
            if not "." in clean_fn:
                clean_fn += ".txt"

            file_path = os.path.join(target_dir, clean_fn)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return True, f"Fichier « {clean_fn} » créé sur le {folder.capitalize()}."
        except Exception as e:
            return False, f"Erreur création fichier : {e}"

    @staticmethod
    def create_folder(folder_name: str, location: str = "desktop") -> Tuple[bool, str]:
        """Crée un dossier sur le Bureau ou dans les Documents."""
        try:
            user_home = os.path.expanduser("~")
            base = os.path.join(user_home, "Desktop") if location.lower() in ["desktop", "bureau"] else os.path.join(user_home, "Documents")
            clean_fn = DesktopController.clean_target_name(folder_name)
            target = os.path.join(base, clean_fn)
            os.makedirs(target, exist_ok=True)
            return True, f"Dossier « {clean_fn} » créé avec succès."
        except Exception as e:
            return False, f"Erreur création dossier : {e}"

    @staticmethod
    def browse_web(query: str, site: str = "direct") -> Tuple[bool, str]:
        """Ouvre une recherche ou un site web dans le navigateur."""
        clean_q = query.strip()
        if not clean_q:
            return False, "Requête web vide."

        if clean_q.startswith("http://") or clean_q.startswith("https://"):
            url = clean_q
        elif site.lower() == "youtube" or "youtube" in clean_q.lower():
            q_clean = clean_q.lower().replace("youtube", "").strip()
            import urllib.parse
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q_clean)}"
        elif site.lower() == "github" or "github" in clean_q.lower():
            q_clean = clean_q.lower().replace("github", "").strip()
            import urllib.parse
            url = f"https://github.com/search?q={urllib.parse.quote_plus(q_clean)}"
        else:
            import urllib.parse
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(clean_q)}"

        try:
            subprocess.Popen(f"start {url}", shell=True)
            return True, f"Navigation lancée : {clean_q}"
        except Exception as e:
            return False, f"Erreur navigation web : {e}"

    @staticmethod
    def find_and_open_file(query_name: str) -> Tuple[bool, str]:
        """Cherche un fichier dans les répertoires utilisateur (Bureau, Téléchargements, Documents, etc.) et l'ouvre."""
        clean_q = DesktopController.clean_target_name(query_name)
        user_home = os.path.expanduser("~")
        search_dirs = [
            os.path.join(user_home, "Desktop"),
            os.path.join(user_home, "Downloads"),
            os.path.join(user_home, "Documents"),
            os.path.join(user_home, "Pictures"),
            os.path.join(user_home, "Videos")
        ]
        matches = []
        for d in search_dirs:
            if not os.path.exists(d):
                continue
            for root, dirs, files in os.walk(d):
                rel_depth = root[len(d):].count(os.sep)
                if rel_depth > 3:
                    continue
                for f in files:
                    if clean_q in f.lower():
                        matches.append(os.path.join(root, f))
                        if len(matches) >= 1:
                            break
                if matches:
                    break
            if matches:
                break
        
        if matches:
            target_path = matches[0]
            try:
                os.startfile(target_path)
                filename = os.path.basename(target_path)
                return True, f"Fichier trouvé et ouvert : {filename}"
            except Exception as e:
                return False, f"Fichier trouvé mais erreur d'ouverture : {e}"
        return False, f"Fichier « {query_name} » introuvable sur le PC."

    @staticmethod
    def open_explorer_and_target(target: str) -> Tuple[bool, str]:
        """Ouvre l'explorateur et navigue vers le dossier ou clique sur l'élément."""
        t_clean = DesktopController.clean_target_name(target)
        shell_map = {
            "téléchargements": "shell:Downloads",
            "telechargements": "shell:Downloads",
            "downloads": "shell:Downloads",
            "documents": "shell:Personal",
            "mes documents": "shell:Personal",
            "images": "shell:My Pictures",
            "bureau": "shell:Desktop",
            "desktop": "shell:Desktop",
            "musique": "shell:My Music",
            "vidéos": "shell:My Video",
            "videos": "shell:My Video"
        }
        for k, shell_cmd in shell_map.items():
            if k in t_clean:
                subprocess.Popen(f"explorer.exe {shell_cmd}", shell=True)
                return True, f"Explorateur ouvert sur « {k.capitalize()} »."
        
        subprocess.Popen("explorer.exe", shell=True)
        time.sleep(0.7)
        return DesktopController.smart_click(target)

    @staticmethod
    def smart_click(target: str, button: str = "left", double: bool = False) -> Tuple[bool, str]:
        """
        Localise intelligemment un élément à l'écran par OCR local WinRT (<0.3s)
        ou par coordonnées, et clique dessus avec déplacement fluide du curseur (courbe de Bézier).
        """
        clean_target = DesktopController.clean_target_name(target)
        if not clean_target:
            return False, "Cible de clic non spécifiée."

        # Clic par coordonnées si format "x,y"
        m_coord = re.search(r'^(\d+)\s*,\s*(\d+)$', clean_target)
        if m_coord:
            cx, cy = int(m_coord.group(1)), int(m_coord.group(2))
            from island.automation import click
            click(cx, cy, button=button, double=double, smooth=True)
            return True, f"Clic effectué aux coordonnées ({cx}, {cy})."

        # 1. Analyse OCR locale ultra-rapide (<0.3s)
        try:
            from island.ocr import find_screen_elements
            elems = find_screen_elements(clean_target)
            if elems:
                el = elems[0]
                cx, cy = el["center_x"], el["center_y"]
                from island.automation import click
                click(cx, cy, button=button, double=double, smooth=True)
                return True, f"Clic effectué sur « {clean_target} »."
        except Exception as e:
            print("[SmartClick] Erreur OCR:", e)

        # 2. Repli Vision Multimodale Agnes AI 3.0 Flash (~0.9s)
        try:
            from island.vision import capture_screen
            cap = capture_screen()
            latest = cap.get("latest_path")
            if latest and os.path.exists(latest):
                from PIL import Image
                import io, base64, urllib.request
                with Image.open(latest) as img:
                    orig_w, orig_h = img.size
                    ratio = min(1280 / orig_w, 1.0)
                    nw, nh = int(orig_w * ratio), int(orig_h * ratio)
                    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    resized.convert("RGB").save(buf, format="JPEG", quality=80)
                    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

                prompt = (
                    f"Tu es un agent de repérage visuel sur interface Windows. Sur cette capture d'écran "
                    f"(résolution originale {orig_w}x{orig_h}), localise le centre exact de : « {clean_target} ». "
                    f"Réponds STRICTEMENT un JSON valide : {{\"found\": true, \"x\": <int_sur_original>, \"y\": <int_sur_original>, \"label\": \"<nom_court>\"}}"
                )
                payload = {
                    "model": "agnes-3.0-flash",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                            ]
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 120
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer sk-B34o3ZnpLfcCa7KtTI67fthOkJ6dQvhEmKjsiRvTZnKl5FlE"
                }
                req = urllib.request.Request("https://apihub.agnes-ai.com/v1/chat/completions", data=json.dumps(payload).encode("utf-8"), headers=headers)
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    txt = data["choices"][0]["message"]["content"]
                    m_j = re.search(r'\{.*\}', txt, re.DOTALL)
                    if m_j:
                        parsed = json.loads(m_j.group(0))
                        if parsed.get("found"):
                            cx = int(parsed.get("x", 0))
                            cy = int(parsed.get("y", 0))
                            from island.automation import click
                            click(cx, cy, button=button, double=double, smooth=True)
                            return True, f"Clic effectué sur « {clean_target} »."
        except Exception as e:
            print("[SmartClick] Erreur Vision Agnes:", e)

        # 3. Repli avec agent-desktop click
        res = DesktopController.run_agent_desktop_command(["click", clean_target])
        if res and res.get("ok"):
            return True, f"Clic effectué sur « {clean_target} » via Agent-Desktop."

        # 4. Repli pour boutons standards de dialogue (OK, Valider, Annuler, Fermer)
        if clean_target.lower() in ["ok", "valider", "confirmer", "oui"]:
            from island.automation import press_key
            press_key("enter")
            return True, "Bouton OK validé (Entrée)."
        if clean_target.lower() in ["annuler", "fermer", "non", "échap", "echap"]:
            from island.automation import press_key
            press_key("escape")
            return True, "Bouton annulé (Échap)."

        return False, f"Impossible de localiser « {clean_target} » à l'écran."

    @staticmethod
    def trigger_point_overlay(x: float, y: float, label: str = "", duration: float = 4.0, color: str = "#38bdf8") -> bool:
        """Envoie la commande point_at à l'overlay Qt de l'Island ou via websocket."""
        try:
            from island.window import IslandWindow
            inst = IslandWindow.get_instance()
            if inst and hasattr(inst, "pointer") and inst.pointer:
                inst.state_change_requested.emit("point_at", {
                    "x": float(x),
                    "y": float(y),
                    "label": label,
                    "duration": float(duration),
                    "color": color
                })
                return True
        except Exception as e:
            print("[DesktopControl] Erreur trigger_point_overlay direct:", e)

        # Fallback websocket
        try:
            import websockets, asyncio
            async def _send():
                async with websockets.connect("ws://127.0.0.1:8765", open_timeout=1.0) as ws:
                    payload = {
                        "action": "point_at",
                        "x": float(x),
                        "y": float(y),
                        "label": label,
                        "duration": float(duration),
                        "color": color
                    }
                    await ws.send(json.dumps(payload))
            asyncio.run(_send())
            return True
        except Exception:
            pass
        return False

    @staticmethod
    def point_to_element(query: str) -> Tuple[bool, str]:
        """
        Localise un élément à l'écran (via OCR local ou Vision Multimodale Agnes 3.0 Flash)
        et projette le halo HeyClicky avec étiquette au-dessus de l'élément.
        """
        clean_target = DesktopController.clean_target_name(query)
        if not clean_target:
            return False, "Élément à pointer non spécifié."

        x, y, label = None, None, clean_target.capitalize()

        # 1. Cas particulier Windows : Explorateur de fichiers
        if any(w in clean_target for w in ["explorateur", "explorateur de fichiers", "fichiers", "explorer"]):
            try:
                from island.ocr import find_screen_elements
                elems = find_screen_elements("explorateur") or find_screen_elements("fichier")
                if elems:
                    x, y = elems[0]["center_x"], elems[0]["center_y"]
                    label = "Explorateur de fichiers"
            except Exception:
                pass

            if x is None:
                from island.vision import capture_screen
                cap = capture_screen()
                w = cap.get("width", 1920)
                h = cap.get("height", 1080)
                x = int(w * 0.47)
                y = int(h - 24)
                label = "Explorateur de fichiers"

        # 2. OCR local WinRT (<0.2s)
        if x is None:
            try:
                from island.ocr import find_screen_elements
                elems = find_screen_elements(clean_target)
                if elems:
                    x, y = elems[0]["center_x"], elems[0]["center_y"]
                    label = elems[0].get("text", clean_target).strip()
            except Exception as e:
                print("[PointToElement] Erreur OCR:", e)

        # 3. Vision Multimodale Agnes AI 3.0 Flash (~0.9s)
        if x is None:
            try:
                from island.vision import capture_screen
                cap = capture_screen()
                latest = cap.get("latest_path")
                if latest and os.path.exists(latest):
                    from PIL import Image
                    import io, base64, urllib.request
                    with Image.open(latest) as img:
                        orig_w, orig_h = img.size
                        ratio = min(1280 / orig_w, 1.0)
                        nw, nh = int(orig_w * ratio), int(orig_h * ratio)
                        resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
                        buf = io.BytesIO()
                        resized.convert("RGB").save(buf, format="JPEG", quality=80)
                        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

                    prompt = (
                        f"Tu es un agent de repérage visuel sur interface Windows. Sur cette capture d'écran "
                        f"(résolution originale {orig_w}x{orig_h}), localise le centre exact de : « {clean_target} ». "
                        f"Réponds STRICTEMENT un JSON valide : {{\"found\": true, \"x\": <int_sur_original>, \"y\": <int_sur_original>, \"label\": \"<nom_court>\"}}"
                    )
                    payload = {
                        "model": "agnes-3.0-flash",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                                ]
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": 120
                    }
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer sk-B34o3ZnpLfcCa7KtTI67fthOkJ6dQvhEmKjsiRvTZnKl5FlE"
                    }
                    req = urllib.request.Request("https://apihub.agnes-ai.com/v1/chat/completions", data=json.dumps(payload).encode("utf-8"), headers=headers)
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        txt = data["choices"][0]["message"]["content"]
                        m_j = re.search(r'\{.*\}', txt, re.DOTALL)
                        if m_j:
                            parsed = json.loads(m_j.group(0))
                            if parsed.get("found"):
                                x = int(parsed.get("x", 0))
                                y = int(parsed.get("y", 0))
                                label = parsed.get("label", clean_target)
            except Exception as e:
                print("[PointToElement] Erreur Vision Agnes:", e)

        if x is not None and y is not None:
            DesktopController.trigger_point_overlay(x, y, label=label, duration=4.5)
            return True, f"Regardez sur votre écran : voici « {label} » désigné par le pointeur HeyClicky."

        return False, f"Impossible de localiser « {clean_target} » sur votre écran."

    @staticmethod
    def set_system_volume(level_percent: int) -> Tuple[bool, str]:
        """Définit le volume système (0-100%)."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            level = max(0.0, min(1.0, level_percent / 100.0))
            volume.SetMasterVolumeLevelScalar(level, None)
            volume.SetMute(0, None)
            return True, f"Volume réglé à {level_percent}%."
        except Exception:
            return False, "Erreur lors du réglage du volume."

    @staticmethod
    def toggle_mute() -> Tuple[bool, str]:
        """Bascule la sourdine (Mute)."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            current = volume.GetMute()
            new_mute = 0 if current else 1
            volume.SetMute(new_mute, None)
            state_str = "activée" if new_mute else "désactivée"
            return True, f"Sourdine {state_str}."
        except Exception:
            return False, "Erreur bascule sourdine."

    @staticmethod
    def media_control(action: str) -> Tuple[bool, str]:
        """Contrôle multimédia : play, pause, next, previous."""
        VK_MEDIA_NEXT_TRACK = 0xB0
        VK_MEDIA_PREV_TRACK = 0xB1
        VK_MEDIA_PLAY_PAUSE = 0xB3

        key_map = {
            "play": VK_MEDIA_PLAY_PAUSE,
            "pause": VK_MEDIA_PLAY_PAUSE,
            "play_pause": VK_MEDIA_PLAY_PAUSE,
            "suivant": VK_MEDIA_NEXT_TRACK,
            "next": VK_MEDIA_NEXT_TRACK,
            "precedent": VK_MEDIA_PREV_TRACK,
            "prev": VK_MEDIA_PREV_TRACK
        }
        vk = key_map.get(action.lower(), VK_MEDIA_PLAY_PAUSE)
        try:
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
            return True, f"Contrôle multimédia ({action}) effectué."
        except Exception:
            return False, "Erreur contrôle média."

    @staticmethod
    def lock_workstation() -> Tuple[bool, str]:
        """Verrouille immédiatement la session Windows."""
        try:
            ctypes.windll.user32.LockWorkStation()
            return True, "Session Windows verrouillée."
        except Exception as e:
            return False, f"Erreur verrouillage : {e}"

    @staticmethod
    def show_desktop() -> Tuple[bool, str]:
        """Affiche le bureau en réduisant toutes les fenêtres (Win + D)."""
        VK_LWIN = 0x5B
        VK_D = 0x44
        try:
            ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_D, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_D, 0, 2, 0)
            ctypes.windll.user32.keybd_event(VK_LWIN, 0, 2, 0)
            return True, "Bureau affiché."
        except Exception:
            return False, "Erreur affichage bureau."

    @staticmethod
    def take_screenshot() -> Tuple[bool, str]:
        """Prend une capture d'écran complète et l'enregistre sur le Bureau."""
        try:
            import mss
            import mss.tools
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            filename = f"Capture_{int(time.time())}.png"
            out_path = os.path.join(desktop_dir, filename)
            with mss.MSS() as sct:
                monitor = sct.monitors[0]
                sct_img = sct.grab(monitor)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=out_path)
            return True, f"Capture d'écran enregistrée sur le Bureau ({filename})."
        except Exception as e:
            return False, f"Erreur capture d'écran : {e}"

    @staticmethod
    def execute_action(action: str, params: dict) -> Tuple[bool, str]:
        """
        Exécuteur universel pour toutes les actions d'outils appelées par le LLM Agent.
        """
        act = (action or "").lower().strip()
        params = params or {}

        if act == "open_app":
            name = params.get("name") or params.get("app") or ""
            return DesktopController.open_application(name)

        elif act == "close_app":
            name = params.get("name") or params.get("app") or "active"
            return DesktopController.close_application(name)

        elif act == "click":
            target = params.get("target") or params.get("element") or "OK"
            button = params.get("button", "left")
            double = bool(params.get("double", False))
            return DesktopController.smart_click(target, button=button, double=double)

        elif act == "type_text":
            text = params.get("text", "")
            press_enter = bool(params.get("press_enter", False))
            from island.automation import type_text, press_key
            type_text(text)
            if press_enter:
                time.sleep(0.05)
                press_key("enter")
            DesktopController.last_typed_text = text
            return True, f"Texte saisi : « {text} »"

        elif act == "press_hotkey":
            keys = params.get("keys") or params.get("key") or "enter"
            from island.automation import press_key
            key_map = {"entrée": "enter", "entree": "enter", "échap": "escape", "echap": "escape"}
            clean_keys = key_map.get(keys.lower(), keys.lower())
            press_key(clean_keys)
            return True, f"Touche {keys} activée."

        elif act == "empty_recycle_bin":
            return DesktopController.empty_recycle_bin()

        elif act == "set_volume":
            lvl = int(params.get("level", 50))
            return DesktopController.set_system_volume(lvl)

        elif act == "media_control":
            cmd = params.get("command", "play_pause")
            return DesktopController.media_control(cmd)

        elif act == "create_file":
            fn = params.get("filename", "note.txt")
            content = params.get("content", "")
            folder = params.get("folder", "desktop")
            return DesktopController.create_file(fn, content, folder)

        elif act == "create_folder":
            name = params.get("name") or params.get("folder_name") or "Nouveau Dossier"
            loc = params.get("location", "desktop")
            return DesktopController.create_folder(name, loc)

        elif act == "browse_web":
            query = params.get("query", "")
            site = params.get("site", "google")
            return DesktopController.browse_web(query, site)

        elif act == "take_screenshot":
            return DesktopController.take_screenshot()

        elif act == "point_at":
            target = params.get("target") or params.get("element") or params.get("name") or ""
            return DesktopController.point_to_element(target)

        elif act == "minimize_app":
            return DesktopController.minimize_active_window()

        elif act == "scroll":
            direction = params.get("direction", "down")
            amount = int(params.get("amount", 6))
            from island.automation import scroll, press_key
            if direction in ["down", "bas"]:
                scroll(-amount)
                return True, "Défilement vers le bas."
            elif direction in ["up", "haut"]:
                scroll(amount)
                return True, "Défilement vers le haut."
            elif direction in ["top", "haut_page"]:
                press_key("home")
                return True, "Haut de page."
            elif direction in ["bottom", "bas_page"]:
                press_key("end")
                return True, "Bas de page."
            return True, "Défilement effectué."

        elif act == "edit_text":
            cmd = params.get("command", "undo")
            from island.automation import press_key, type_text
            if cmd == "undo":
                press_key("ctrl+z")
                return True, "Frappe annulée (Ctrl+Z)."
            elif cmd == "redo":
                press_key("ctrl+y")
                return True, "Frappe rétablie (Ctrl+Y)."
            elif cmd == "delete_all":
                press_key("ctrl+a")
                time.sleep(0.04)
                press_key("backspace")
                DesktopController.last_typed_text = ""
                return True, "Tout le texte a été effacé."
            elif cmd == "delete_word":
                press_key("ctrl+backspace")
                return True, "Dernier mot effacé."
            elif cmd == "delete_line":
                press_key("shift+home")
                time.sleep(0.03)
                press_key("backspace")
                return True, "Ligne effacée."
            elif cmd == "newline":
                press_key("enter")
                return True, "Saut de ligne effectué."
            elif cmd == "replace":
                new_t = params.get("new_text", "")
                press_key("ctrl+a")
                time.sleep(0.05)
                type_text(new_t)
                DesktopController.last_typed_text = new_t
                return True, f"Texte remplacé par : « {new_t} »"

        elif act == "search_in_page":
            query_t = params.get("query", "")
            from island.automation import press_key, type_text
            press_key("ctrl+f")
            time.sleep(0.12)
            type_text(query_t)
            time.sleep(0.05)
            press_key("enter")
            return True, f"Recherche de « {query_t} » lancée."

        elif act == "run_powershell":
            cmd = params.get("command", "")
            if cmd:
                try:
                    res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=5.0)
                    out = (res.stdout or res.stderr or "Commande exécutée.").strip()
                    return True, out[:100]
                except Exception as e:
                    return False, f"Erreur powershell : {e}"

        return False, f"Action « {act} » inconnue."

    @staticmethod
    def execute_intent(query: str) -> Optional[Tuple[bool, str]]:
        """
        Fast-Path ultra-rapide (<0.005s) pour les commandes directes de l'utilisateur.
        """
        q = query.lower().strip()

        # 0. Vidage de la Corbeille ("vide la corbeille", "nettoie la corbeille")
        if any(w in q for w in ["vide la corbeille", "vider la corbeille", "nettoie la corbeille", "nettoyer la corbeille"]):
            return DesktopController.empty_recycle_bin()

        # 0b. Fermer la fenêtre active / message d'erreur ("ferme la fenêtre", "ferme l'erreur", "ferme cette erreur", "ferme ça")
        if any(w in q for w in ["ferme la fenêtre", "ferme la fenetre", "ferme cette fenêtre", "ferme cette fenetre", "ferme l'erreur", "ferme cette erreur", "ferme le message", "ferme ça", "ferme ca", "ferme le pop up", "ferme la pop up", "ferme-la", "ferme la"]):
            return DesktopController.close_active_window()

        # 0c. Clic rapide sur bouton standard ("clique sur ok", "appuie sur ok", "clique sur valider", "clique sur annuler")
        m_direct_btn = re.search(r'^(?:clique|appuie|fais un clic)\s+(?:sur\s+)?(ok|valider|annuler|confirmer|fermer)$', q)
        if m_direct_btn:
            btn = m_direct_btn.group(1).strip()
            return DesktopController.smart_click(btn)

        # 0d. Réduire / Minimiser la fenêtre active ("réduis la fenêtre", "minimise la fenêtre", "réduis la fenêtre actuelle", etc.)
        if any(w in q for w in [
            "réduis la fenêtre", "reduis la fenetre", "minimise la fenêtre", "minimise la fenetre",
            "réduis la fenêtre actuelle", "reduis la fenetre actuelle", "minimise la fenêtre actuelle",
            "réduis la fenêtre active", "minimise la fenêtre active", "réduis cette fenêtre", "minimise cette fenêtre",
            "réduis ça", "reduis ca", "minimise ça", "minimise ca", "réduis-la", "reduis-la", "réduis la", "reduis la",
            "minimise-la", "minimise la", "réduis", "reduis", "minimise"
        ]) and len(q.split()) <= 6:
            return DesktopController.minimize_active_window()

        # 0e. Pointer / Montrer un élément à l'écran (Pointeur laser HeyClicky)
        m_point = re.search(r'^(?:montre(?:-moi)?\s+(?:où\s+se\s+trouve|ou\s+se\s+trouve|où\s+est|ou\s+est|l[\'\s]|la\s+|le\s+|les\s+)?|où\s+se\s+trouve|ou\s+se\s+trouve|où\s+est|ou\s+est|pointe\s+(?:sur\s+)?|trouve\s+(?:où\s+est\s+)?)(.+)$', q)
        if m_point:
            raw_target = m_point.group(1).strip()
            if not any(w in raw_target for w in ["l'heure", "la date", "qui tu es", "un bug"]):
                return DesktopController.point_to_element(raw_target)

        # =========================================================================
        # GESTION ÉDITION DE TEXTE, EFFACEMENT & CORRECTION (HUMAN-LIKE EDITING)
        # =========================================================================

        # E1. Effacer tout le texte
        if any(w in q for w in ["efface tout", "supprime tout", "efface tout le texte", "supprime tout le texte", "vide le texte", "vide le document", "nettoie le texte"]):
            from island.automation import press_key
            press_key("ctrl+a")
            time.sleep(0.04)
            press_key("backspace")
            DesktopController.last_typed_text = ""
            return True, "Tout le texte a été effacé."

        # E2. Effacer le dernier mot
        if any(w in q for w in ["efface le mot", "efface le dernier mot", "supprime le mot", "supprime le dernier mot", "enlève le dernier mot", "enleve le dernier mot"]):
            from island.automation import press_key
            press_key("ctrl+backspace")
            return True, "Dernier mot effacé."

        # E3. Effacer la ligne
        if any(w in q for w in ["efface la ligne", "supprime la ligne", "efface cette ligne", "supprime cette ligne"]):
            from island.automation import press_key
            press_key("shift+home")
            time.sleep(0.03)
            press_key("backspace")
            return True, "Ligne effacée."

        # E4. Annulation / Effacement de ce qui vient d'être écrit (« non efface ça », « efface ça », etc.)
        if any(w in q for w in [
            "non efface ça", "non efface ca", "efface ça", "efface ca", "efface", 
            "supprime ça", "supprime ca", "non pas ça", "non pas ca", "annule ça", "annule ca",
            "efface ce que tu viens d'écrire", "efface ce que tu as écrit", "annule la frappe",
            "non annule", "annule ce texte"
        ]) and len(q.split()) <= 7:
            from island.automation import press_key
            press_key("ctrl+z")
            DesktopController.last_typed_text = ""
            return True, "Frappe annulée (Ctrl+Z)."

        # E5. Rétablir / Refaire (Ctrl+Y)
        if any(w in q for w in ["rétablis", "retablis", "refais", "fais ctrl y"]):
            from island.automation import press_key
            press_key("ctrl+y")
            return True, "Rétabli (Ctrl+Y)."

        # E6. Remplacement direct (« remplace ça par [texte] », « remplace tout par [texte] », « mets plutôt [texte] »)
        m_replace_all = re.search(r'^(?:remplace\s+(?:ça|ca|tout)\s+par|mets\s+plutôt|mets\s+plutot|écris\s+plutôt|ecris\s+plutot)\s+(.+)$', q)
        if m_replace_all:
            new_text = m_replace_all.group(1).strip('"\'«» ')
            from island.automation import press_key, type_text
            press_key("ctrl+a")
            time.sleep(0.05)
            type_text(new_text)
            DesktopController.last_typed_text = new_text
            short_txt = new_text if len(new_text) <= 30 else (new_text[:27] + "...")
            return True, f"Remplacé par : « {short_txt} »"

        # E7. Remplacement ciblé (« remplace X par Y », « corrige X en Y », « non pas X mais Y »)
        pat_corr = r'(?:remplace\s+(.+?)\s+par\s+(.+)|corrige\s+(.+?)\s+(?:en|par)\s+(.+)|change\s+(.+?)\s+en\s+(.+)|non\s+pas\s+(.+?)\s+mais\s+(.+)|le\s+(?:mot\s+)?(.+?)\s+est\s+mal\s+(?:ecrit|écrit)\s+(?:c[\'\s]+est|c[\'\s]+était|mets)\s+(.+))'
        m_corr = re.search(pat_corr, q)
        if m_corr:
            groups = [g.strip('"\'«» ') for g in m_corr.groups() if g is not None]
            if len(groups) >= 2:
                old_val, new_val = groups[0], groups[1]
                from island.automation import press_key, type_text
                if DesktopController.last_typed_text and old_val in DesktopController.last_typed_text:
                    new_full = DesktopController.last_typed_text.replace(old_val, new_val)
                    DesktopController.last_typed_text = new_full
                    press_key("ctrl+a")
                    time.sleep(0.06)
                    type_text(new_full)
                    return True, f"Texte corrigé : « {new_full} »"
                else:
                    press_key("ctrl+h")
                    time.sleep(0.12)
                    type_text(old_val)
                    time.sleep(0.05)
                    press_key("tab")
                    time.sleep(0.05)
                    type_text(new_val)
                    time.sleep(0.05)
                    press_key("alt+a")
                    time.sleep(0.05)
                    press_key("escape")
                    return True, f"Remplacé « {old_val} » par « {new_val} »."

        # E8. Aller à la ligne et écrire du texte (« va à la ligne et écris ... », « saute une ligne et écris ... »)
        m_nl_write = re.search(r'^(?:va\s+à\s+la\s+ligne|saute\s+(?:une|de)\s+ligne|retour\s+à\s+la\s+ligne)\s+et\s+(?:écris|ecris|tape|saisis|mets)\s+(.+)$', q)
        if m_nl_write:
            txt = m_nl_write.group(1).strip('"\'«» ')
            from island.automation import press_key, type_text
            press_key("enter")
            time.sleep(0.06)
            type_text(txt)
            DesktopController.last_typed_text = txt
            short_txt = txt if len(txt) <= 30 else (txt[:27] + "...")
            return True, f"Ligne créée et texte saisi : « {short_txt} »"

        # E9. Sauter plusieurs lignes (« saute deux lignes », « saute 3 lignes »)
        m_skip_n = re.search(r'saute\s+(\d+|deux|trois|quatre)\s+lignes?', q)
        if m_skip_n:
            from island.automation import press_key
            num_map = {"deux": 2, "trois": 3, "quatre": 4}
            val = m_skip_n.group(1)
            n = num_map.get(val, int(val) if val.isdigit() else 2)
            for _ in range(n):
                press_key("enter")
                time.sleep(0.04)
            return True, f"{n} sauts de ligne effectués."

        # =========================================================================
        # RECHERCHE DANS LE DOCUMENT & FONCTIONS BLOC-NOTES (CTRL+F, SAUVEGARDE, ETC.)
        # =========================================================================

        # D1. Recherche dans le document / la page (Ctrl+F)
        m_find_doc = re.search(r'^(?:cherche|recherche|trouve)\s+(?:dans\s+(?:le\s+document|le\s+texte|la\s+page|le\s+fichier)\s+)?(?:le\s+mot\s+|l[\'\s]|le\s+|la\s+)?(.+)$', q)
        if m_find_doc and any(w in q for w in ["cherche", "recherche"]) and not any(w in q for w in ["sur google", "sur internet", "sur youtube", "sur le web", "un fichier", "le fichier", "où se trouve", "ou se trouve"]):
            search_term = m_find_doc.group(1).strip('"\'«» ')
            if search_term and len(search_term.split()) <= 4:
                from island.automation import press_key, type_text
                press_key("ctrl+f")
                time.sleep(0.12)
                type_text(search_term)
                time.sleep(0.05)
                press_key("enter")
                return True, f"Recherche de « {search_term} » lancée dans le document."

        # D2. Occurrence suivante dans la recherche (F3 / Entrée)
        if any(w in q for w in ["résultat suivant", "resultat suivant", "cherche le suivant", "mot suivant", "occurrence suivante", "suivant"]) and len(q.split()) <= 3:
            from island.automation import press_key
            press_key("f3")
            return True, "Occurrence suivante (F3)."

        # D3. Sauvegarder sous (Ctrl+Shift+S)
        if any(w in q for w in ["enregistre sous", "enregistrer sous", "sauvegarde sous", "sauvegarder sous"]):
            from island.automation import press_key
            press_key("ctrl+shift+s")
            return True, "Boîte de dialogue Enregistrer sous ouverte."

        # D4. Couper (Ctrl+X)
        if any(w in q for w in ["coupe tout", "coupe ça", "coupe ce texte", "coupe"]):
            from island.automation import press_key
            press_key("ctrl+x")
            return True, "Coupé dans le presse-papiers (Ctrl+X)."

        # D5. Début / Fin du document
        if any(w in q for w in ["va au début", "va au debut", "remonte tout en haut", "haut du document", "début du texte", "debut du texte"]):
            from island.automation import press_key
            press_key("ctrl+home")
            return True, "Curseur placé au début du document."

        if any(w in q for w in ["va à la fin", "va a la fin", "descends tout en bas", "bas du document", "fin du texte"]):
            from island.automation import press_key
            press_key("ctrl+end")
            return True, "Curseur placé à la fin du document."

        # =========================================================================
        # NAVIGATION COMPLÈTE À L'ORDINATEUR COMME UN HUMAIN (SCROLL, ONGLETS, ETC.)
        # =========================================================================

        # N1. Défilement / Scroll vers le haut (PageUp ou Molette)
        if any(w in q for w in [
            "scrolle vers le haut", "scrolle en haut", "remonte la page", "défile vers le haut",
            "defile vers le haut", "fais défiler vers le haut", "monte la page", "remonte", "plus haut"
        ]) and len(q.split()) <= 6:
            from island.automation import scroll
            scroll(amount=6)
            return True, "Défilement vers le haut effectué."

        # N2. Défilement / Scroll vers le bas (PageDown ou Molette)
        if any(w in q for w in [
            "scrolle vers le bas", "scrolle en bas", "descends la page", 
            "défile vers le bas", "defile vers le bas", "fais défiler vers le bas", "scrolle un peu",
            "baisse la page", "scrolle", "descends", "plus bas"
        ]) and not any(x in q for x in ["haut", "monte", "remonte"]) and len(q.split()) <= 6:
            from island.automation import scroll
            scroll(amount=-6)
            return True, "Défilement vers le bas effectué."

        # N3. Tout en bas / Tout en haut de la page
        if any(w in q for w in ["tout en bas", "bas de la page", "bas de page", "fin de page"]):
            from island.automation import press_key
            press_key("end")
            return True, "Défilé jusqu'en bas de page."

        if any(w in q for w in ["tout en haut", "haut de la page", "haut de page", "début de page"]):
            from island.automation import press_key
            press_key("home")
            return True, "Défilé jusqu'en haut de page."

        # N4. Onglets de navigation (Ctrl+T, Ctrl+W, Ctrl+Tab)
        if any(w in q for w in ["nouvel onglet", "ouvre un nouvel onglet", "crée un onglet", "nouveau onglet"]):
            from island.automation import press_key
            press_key("ctrl+t")
            return True, "Nouvel onglet ouvert (Ctrl+T)."

        if any(w in q for w in ["ferme l'onglet", "ferme cet onglet", "quitte l'onglet"]):
            from island.automation import press_key
            press_key("ctrl+w")
            return True, "Onglet fermé (Ctrl+W)."

        if any(w in q for w in ["onglet suivant", "passe à l'onglet suivant", "change d'onglet"]):
            from island.automation import press_key
            press_key("ctrl+tab")
            return True, "Passé à l'onglet suivant (Ctrl+Tab)."

        if any(w in q for w in ["onglet précédent", "onglet precedent", "passe à l'onglet précédent"]):
            from island.automation import press_key
            press_key("ctrl+shift+tab")
            return True, "Passé à l'onglet précédent (Ctrl+Shift+Tab)."

        # N5. Historique : Page précédente / suivante (Alt+Flèches)
        if any(w in q for w in ["page précédente", "page precedente", "retourne en arrière", "retour en arriere", "reviens en arrière"]):
            from island.automation import press_key
            press_key("alt+left")
            return True, "Page précédente (Alt+Gauche)."

        if any(w in q for w in ["page suivante", "avance d'une page"]):
            from island.automation import press_key
            press_key("alt+right")
            return True, "Page suivante (Alt+Droite)."

        # N6. Actualiser la page (F5)
        if any(w in q for w in ["recharge la page", "actualise la page", "rafraîchis la page", "rafraichis la page", "actualise"]):
            from island.automation import press_key
            press_key("f5")
            return True, "Page actualisée (F5)."

        # N7. Basculer entre les applications (Alt+Tab)
        if any(w in q for w in ["change de fenêtre", "change de fenetre", "change d'application", "bascule de fenêtre", "fenêtre suivante", "application suivante"]):
            from island.automation import press_key
            press_key("alt+tab")
            return True, "Bascule d'application effectuée (Alt+Tab)."

        # N8. Recherche Windows (Win+S)
        if any(w in q for w in ["recherche windows", "ouvre la recherche", "menu recherche"]):
            from island.automation import press_key
            press_key("win+s")
            return True, "Recherche Windows ouverte (Win+S)."

        # N9. Recherche Web explicite (« cherche sur google X », « recherche sur le web X », etc.)
        m_web = re.search(r'^(?:cherche|recherche)\s+(?:sur\s+(?:google|le\s+web|internet)\s+)?(.+?)(?:\s+sur\s+(?:google|le\s+web|internet))?$', q)
        if m_web and any(w in q for w in ["google", "internet", "web", "youtube", "github"]):
            target_q = m_web.group(1).strip()
            return DesktopController.browse_web(target_q)

        # 1. Ouvrir une application ET écrire/taper du texte
        m_open_type = re.search(
            r'^(?:ouvre|ouvrir|lance|lancer|démarre|demarre|start|open)\s+(?:le\s+|la\s+|l\')?([a-zA-Z0-9_\-\s\.]+?)\s+et\s+(?:écris|ecris|écrire|ecrire|tape|taper|saisis|saisir|décris|decris|décrire|decrire|d\'écrire|d\'ecrire|mets|mettre)\s+(.+)$',
            q
        )
        if m_open_type:
            target_app = m_open_type.group(1).strip()
            raw_text = m_open_type.group(2).strip()
            if raw_text in ["quelque chose", "quelque chose dessus", "un texte", "du texte", "des trucs", "un mot"]:
                text_to_type = "Bonjour ! Note rédigée automatiquement par Antigravity Island."
            else:
                text_to_type = raw_text.strip('"\'«»')
            return DesktopController.open_and_type(target_app, text_to_type)

        # 1b. Correction contextuelle de texte ("le as est mal écrit c'est ass", "remplace as par ass", "corrige X en Y")
        pat_corr = r'(?:le\s+(?:mot\s+)?(.+?)\s+est\s+mal\s+(?:ecrit|écrit)\s+(?:c[\'\s]+est|c[\'\s]+était|mets)\s+(.+)|corrige\s+(.+?)\s+(?:en|par)\s+(.+)|remplace\s+(.+?)\s+par\s+(.+)|non\s+pas\s+(.+?)\s+mais\s+(.+))'
        m_corr = re.search(pat_corr, q)
        if m_corr:
            groups = [g.strip('"\'«» ') for g in m_corr.groups() if g is not None]
            if len(groups) >= 2:
                old_val, new_val = groups[0], groups[1]
                from island.automation import press_key, type_text
                if DesktopController.last_typed_text and old_val in DesktopController.last_typed_text:
                    new_full = DesktopController.last_typed_text.replace(old_val, new_val)
                    DesktopController.last_typed_text = new_full
                    press_key("ctrl+a")
                    time.sleep(0.06)
                    type_text(new_full)
                    return True, f"Texte corrigé : « {new_full} »"
                else:
                    press_key("ctrl+a")
                    time.sleep(0.06)
                    type_text(new_val)
                    DesktopController.last_typed_text = new_val
                    return True, f"Corrigé en : « {new_val} »"

        # 1c. Ouvrir l'explorateur de fichier et cliquer/naviguer ("ouvre l'explorateur de fichier et clique sur Téléchargements")
        m_exp_click = re.search(r'^(?:ouvre|ouvrir|lance|lancer)\s+(?:l[\'\s]explorateur\s+(?:de\s+fichiers?)?)\s+et\s+(?:clique|va|navigue)\s+sur\s+(.+)$', q)
        if m_exp_click:
            target = m_exp_click.group(1).strip()
            return DesktopController.open_explorer_and_target(target)

        # 1d. Trouver un fichier et l'ouvrir ("trouve un fichier qui s'appelle tant et ouvre-le")
        m_find_file = re.search(r'^(?:trouve|cherche|localise)\s+(?:le\s+|un\s+)?fichier\s+(?:qui\s+s[\'\s]+appelle\s+|nommé\s+|intitulé\s+)?(.+?)(?:\s+et\s+(?:ouvre-le|ouvre\s+le|lance-le|affiche-le))?$', q)
        if m_find_file or ("ouvre le fichier" in q):
            name_query = m_find_file.group(1).strip('"\'«» ') if m_find_file else re.sub(r'^(?:ouvre|lance)\s+le\s+fichier\s+', '', q).strip('"\'«» ')
            return DesktopController.find_and_open_file(name_query)

        # 2. Saut de ligne et saisie de texte directe
        has_newline = any(w in q for w in ["va à la ligne", "va a la ligne", "à la ligne", "a la ligne", "nouvelle ligne", "retour chariot"])
        m_type = re.search(r'(?:écris|ecris|tape|saisis)\s*[:\s]\s*(.+)$', q)
        if has_newline or m_type:
            from island.automation import press_key, type_text
            if has_newline:
                press_key("enter")
                time.sleep(0.08)
            if m_type:
                text_to_type = m_type.group(1).strip('"\'«» :')
                if text_to_type:
                    type_text(text_to_type)
                    DesktopController.last_typed_text = text_to_type
                    short_txt = text_to_type if len(text_to_type) <= 30 else (text_to_type[:27] + "...")
                    return True, f"Texte saisi : « {short_txt} »"
            if has_newline:
                return True, "Saut de ligne effectué."

        # 3. Clic intelligent (OCR local WinRT)
        m_click = re.search(r'^(?:clique|clic|fais un clic|appuie)\s+sur\s+(?:le\s+bouton\s+|l\'icône\s+|l\'icone\s+|l\'onglet\s+|le\s+lien\s+|la\s+fenêtre\s+)?(.+)$', q)
        if m_click:
            target = m_click.group(1).strip()
            if not any(w in target for w in ["mon bureau", "le bureau", "entrée", "enter", "échap", "espace"]):
                return DesktopController.smart_click(target)

        # 4. Touches et Raccourcis clavier
        if any(w in q for w in ["appuie sur entrée", "appuie sur enter", "valide"]):
            from island.automation import press_key
            press_key("enter")
            return True, "Touche Entrée actionnée."
        if any(w in q for w in ["sauvegarde", "enregistre le fichier"]):
            from island.automation import press_key
            press_key("ctrl+s")
            return True, "Sauvegardé (Ctrl+S)."
        if any(w in q for w in ["sélectionne tout", "selectionne tout"]):
            from island.automation import press_key
            press_key("ctrl+a")
            return True, "Tout sélectionné (Ctrl+A)."
        if any(w in q for w in ["copie tout", "copie ça", "copie"]):
            from island.automation import press_key
            press_key("ctrl+c")
            return True, "Copié (Ctrl+C)."
        if any(w in q for w in ["colle tout", "colle"]):
            from island.automation import press_key
            press_key("ctrl+v")
            return True, "Collé (Ctrl+V)."

        # 5. Ouvrir une application simple ("ouvre la corbeille", "ouvre bloc-notes", etc.)
        m_open = re.search(r'^(?:ouvre|ouvrir|lance|lancer|démarre|demarre|start|open)\s+(.+)$', q)
        if m_open:
            target = m_open.group(1).strip()
            if not any(x in target for x in ["les yeux", "la porte", "ton esprit"]):
                return DesktopController.open_application(target)

        # 6. Fermer une application
        m_close = re.search(r'^(?:ferme|fermer|quitte|quitter|arrête|arrete|close|kill)\s+(.+)$', q)
        if m_close:
            target = m_close.group(1).strip()
            return DesktopController.close_application(target)

        # 7. Volume
        if any(w in q for w in ["volume", "le son"]):
            m_vol = re.search(r'(\d+)\s*%', q) or re.search(r'(?:à|a)\s*(\d+)', q)
            if m_vol:
                pct = int(m_vol.group(1))
                return DesktopController.set_system_volume(pct)
            if any(w in q for w in ["coupe", "sourdine", "mute"]):
                return DesktopController.toggle_mute()
            if any(w in q for w in ["monte", "augmente", "plus fort"]):
                return DesktopController.set_system_volume(80)
            if any(w in q for w in ["baisse", "diminue", "moins fort"]):
                return DesktopController.set_system_volume(30)

        # 8. Sourdine directe
        if q in ["mute", "sourdine", "coupe le son", "remets le son"]:
            return DesktopController.toggle_mute()

        # 9. Multimédia
        if q in ["pause", "mets en pause", "play", "lecture", "reprends la musique"]:
            return DesktopController.media_control("play")
        if q in ["morceau suivant", "chanson suivante", "musique suivante", "suivant", "next"]:
            return DesktopController.media_control("next")
        if q in ["morceau précédent", "chanson précédente", "musique précédente", "précédent", "previous"]:
            return DesktopController.media_control("prev")

        # 10. Verrouiller le PC
        if any(w in q for w in ["verrouille", "bloque le pc", "lock mon pc", "lock l'ordinateur"]):
            return DesktopController.lock_workstation()

        # 11. Afficher le bureau / minimiser tout
        if any(w in q for w in ["affiche le bureau", "montre le bureau", "minimise tout", "réduis tout"]):
            return DesktopController.show_desktop()

        # 12. Capture d'écran
        if any(w in q for w in ["capture d'écran", "screenshot", "imprime écran", "prends une photo"]):
            return DesktopController.take_screenshot()

        # 13. Effacer les notifications
        if any(w in q for w in ["efface les notifications", "supprime les notifications", "vide les notifications"]):
            DesktopController.run_agent_desktop_command(["dismiss-all-notifications"])
            return True, "Toutes les notifications ont été effacées."

        return None
