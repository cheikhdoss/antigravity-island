import ctypes
from ctypes import wintypes
import psutil

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

all_windows = []

def enum_cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            ex_style = user32.GetWindowLongW(hwnd, -20)
            is_iconic = bool(user32.IsIconic(hwnd))
            if not (ex_style & 0x00000080):
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                try:
                    proc_name = psutil.Process(pid.value).name()
                except Exception:
                    proc_name = "unknown"
                all_windows.append({"hwnd": hwnd, "title": title, "minimized": is_iconic, "proc": proc_name})
    return True

user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
print(f"Total visible top-level windows: {len(all_windows)}")
for w in all_windows[:15]:
    print(f"  [{'MIN' if w['minimized'] else 'ACT'}] {w['proc']} : {w['title'][:50]}")
