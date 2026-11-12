import ctypes
from ctypes import wintypes
import psutil
import sys
import os

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Signatures Win32 strictes 64-bit
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL

user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL

user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL

user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

GetWindowLongPtrW = getattr(user32, 'GetWindowLongPtrW', user32.GetWindowLongW)
GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
GetWindowLongPtrW.restype = ctypes.c_ssize_t

user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL

user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

user32.OpenDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.OpenDesktopW.restype = wintypes.HDESK

user32.EnumDesktopWindows.argtypes = [wintypes.HDESK, WNDENUMPROC, wintypes.LPARAM]
user32.EnumDesktopWindows.restype = wintypes.BOOL

user32.CloseDesktop.argtypes = [wintypes.HDESK]
user32.CloseDesktop.restype = wintypes.BOOL

class MinimizedWindowTracker:
    """
    Gestionnaire robuste, ultra-léger et 100% thread-safe des fenêtres actives et réduites.
    Ne manipule aucun objet graphique Qt dans les callbacks système Win32.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MinimizedWindowTracker, cls).__new__(cls)
            cls._instance._init_tracker()
        return cls._instance

    def _init_tracker(self):
        self._current_results = []
        self._only_minimized = False
        self._fg_hwnd = 0
        self._gui_icon_cache = {}
        # Référence persistante du callback ctypes
        self._c_callback = WNDENUMPROC(self._enum_callback)

    def _enum_callback(self, hwnd, lparam):
        try:
            if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
                return 1

            is_min = bool(user32.IsIconic(hwnd))
            if self._only_minimized and not is_min:
                return 1

            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0 or length > 500:
                return 1

            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()

            if not title or title in [
                "Program Manager", "Settings", "Antigravity Island", 
                "Windows Input Experience", "Task Switching", "Cortana", "Search", "Start"
            ]:
                return 1

            ex_style = GetWindowLongPtrW(hwnd, -20)  # GWL_EXSTYLE
            # WS_EX_TOOLWINDOW = 0x00000080
            if ex_style & 0x00000080:
                return 1

            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            app_name = title
            try:
                p = psutil.Process(pid.value)
                raw_name = p.name().lower()
                if "chrome" in raw_name: app_name = "Google Chrome"
                elif "code" in raw_name: app_name = "VS Code"
                elif "notepad" in raw_name: app_name = "Bloc-notes"
                elif "explorer" in raw_name: app_name = "Explorateur"
                elif "edge" in raw_name: app_name = "Microsoft Edge"
                elif "spotify" in raw_name: app_name = "Spotify"
                elif "discord" in raw_name: app_name = "Discord"
                elif "telegram" in raw_name: app_name = "Telegram"
                elif "whatsapp" in raw_name: app_name = "WhatsApp"
                elif "slack" in raw_name: app_name = "Slack"
                elif "powershell" in raw_name or "pwsh" in raw_name: app_name = "PowerShell"
                elif "cmd" in raw_name: app_name = "Invite de commandes"
                else: app_name = p.name().replace(".exe", "").capitalize()
            except Exception:
                pass

            # Données 100% primitives (zéro objet Qt dans le callback système)
            self._current_results.append({
                "hwnd": hwnd,
                "title": title,
                "app_name": app_name,
                "is_minimized": is_min,
                "is_active": (hwnd == self._fg_hwnd)
            })
        except Exception:
            pass

        return 1

    def get_windows(self, only_minimized: bool = False):
        self._current_results = []
        self._only_minimized = only_minimized
        try:
            self._fg_hwnd = user32.GetForegroundWindow()
        except Exception:
            self._fg_hwnd = 0

        try:
            user32.EnumWindows(self._c_callback, 0)
        except Exception as e:
            print("[WindowManager] EnumWindows error:", e)

        # Si EnumWindows n'a rien trouvé (ex: exebox/sandbox ou session séparée), basculer sur le desktop 'default'
        if len(self._current_results) == 0:
            try:
                h_desk = user32.OpenDesktopW("default", 0, False, 0x0100)
                if h_desk:
                    user32.EnumDesktopWindows(h_desk, self._c_callback, 0)
                    user32.CloseDesktop(h_desk)
            except Exception as e:
                print("[WindowManager] EnumDesktopWindows error:", e)

        # Pré-chauffage des icônes GUI EN DEHORS du paintEvent
        for w in self._current_results:
            app_name = w.get("app_name", "")
            if app_name and app_name not in self._gui_icon_cache:
                self.get_app_icon(app_name, allow_generate=True)

        return list(self._current_results)

    def get_minimized_windows(self):
        return self.get_windows(only_minimized=True)

    def get_all_open_windows(self):
        return self.get_windows(only_minimized=False)

    def get_app_icon(self, app_name: str, allow_generate: bool = True):
        """Récupère ou génère l'icône vectorielle pure en thread GUI principal (hors paintEvent si allow_generate=False)."""
        if not app_name:
            return None
        if app_name not in self._gui_icon_cache:
            if not allow_generate:
                return None
            try:
                from PyQt6.QtWidgets import QApplication
                if QApplication.instance() is None:
                    return None
                from island.logos import get_app_logo
                self._gui_icon_cache[app_name] = get_app_logo(app_name, 32)
            except Exception:
                return None
        return self._gui_icon_cache.get(app_name)

    def activate_window(self, hwnd):
        """Active la fenêtre cible (la restaure si minimisée, la passe au premier plan)."""
        try:
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            else:
                user32.ShowWindow(hwnd, 5)  # SW_SHOW
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            return True
        except Exception as e:
            print("[WindowManager] Activate error:", e)
            return False

    def close_window(self, hwnd):
        """Ferme la fenêtre cible proprement via WM_CLOSE."""
        try:
            user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
            return True
        except Exception:
            return False

    def restore_window(self, hwnd):
        return self.activate_window(hwnd)

AppWindowManager = MinimizedWindowTracker
