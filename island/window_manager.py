import ctypes
from ctypes import wintypes
import psutil
from PyQt6.QtWidgets import QApplication, QFileIconProvider
from PyQt6.QtCore import QFileInfo
from PyQt6.QtGui import QIcon, QPixmap
import sys

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

class MinimizedWindowTracker:
    def __init__(self):
        self.provider = QFileIconProvider()
        self.icon_cache = {}

    def get_minimized_windows(self):
        minimized = []

        def enum_cb(hwnd, lparam):
            if not user32.IsWindow(hwnd):
                return True
            if not user32.IsWindowVisible(hwnd):
                return True
            if not user32.IsIconic(hwnd):
                return True

            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True

            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()

            if not title or title in ["Program Manager", "Settings", "Antigravity Island"]:
                return True

            ex_style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
            # WS_EX_TOOLWINDOW = 0x00000080
            if ex_style & 0x00000080:
                return True

            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            exe_path = ""
            app_name = title
            try:
                p = psutil.Process(pid.value)
                exe_path = p.exe()
                app_name = p.name().replace(".exe", "").capitalize()
            except Exception:
                pass

            icon_pixmap = None
            if exe_path:
                if exe_path not in self.icon_cache:
                    pix = self.provider.icon(QFileInfo(exe_path)).pixmap(24, 24)
                    if not pix.isNull():
                        self.icon_cache[exe_path] = pix
                icon_pixmap = self.icon_cache.get(exe_path)

            minimized.append({
                "hwnd": hwnd,
                "title": title,
                "app_name": app_name,
                "exe_path": exe_path,
                "pixmap": icon_pixmap
            })
            return True

        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        return minimized

    def restore_window(self, hwnd):
        try:
            # SW_RESTORE = 9
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            print("Restore error:", e)
            return False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    tracker = MinimizedWindowTracker()
    wins = tracker.get_minimized_windows()
    print("Found minimized windows:", len(wins))
    for w in wins:
        print(" -", w["app_name"], ":", w["title"])
