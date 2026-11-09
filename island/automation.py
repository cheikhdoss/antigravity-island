import ctypes
import time
import math

class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

user32 = ctypes.windll.user32

# Constantes des événements souris Windows
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800

# Constantes clavier
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

def get_cursor_position() -> tuple:
    """Retourne la position actuelle du curseur Windows (x, y)."""
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return int(pt.x), int(pt.y)

def set_cursor_position(x: int, y: int):
    """Positionne immédiatement le curseur Windows."""
    user32.SetCursorPos(int(x), int(y))

def move_cursor_smooth(target_x: int, target_y: int, duration: float = 0.35, steps: int = 25):
    """
    Déplace le curseur Windows de manière fluide le long d'une courbe de Bézier
    avec amorti naturel (inspiré du vol de curseur de HeyClicky).
    """
    x0, y0 = get_cursor_position()
    dx = target_x - x0
    dy = target_y - y0
    dist = math.hypot(dx, dy)
    
    if dist < 6:
        set_cursor_position(target_x, target_y)
        return

    # Arc naturel avec points de contrôle décalés
    ctrl_offset = min(60.0, dist * 0.15)
    cx1 = x0 + dx * 0.3 - (dy / dist) * ctrl_offset
    cy1 = y0 + dy * 0.3 + (dx / dist) * ctrl_offset
    cx2 = x0 + dx * 0.7 - (dy / dist) * (ctrl_offset * 0.5)
    cy2 = y0 + dy * 0.7 + (dx / dist) * (ctrl_offset * 0.5)

    delay = duration / steps

    for step in range(1, steps + 1):
        t = step / steps
        # Easing cubic-out : ralenti fluide à l'approche de la cible
        t_eased = 1.0 - math.pow(1.0 - t, 3)
        u = 1.0 - t_eased
        x = (u**3 * x0) + (3 * u**2 * t_eased * cx1) + (3 * u * t_eased**2 * cx2) + (t_eased**3 * target_x)
        y = (u**3 * y0) + (3 * u**2 * t_eased * cy1) + (3 * u * t_eased**2 * cy2) + (t_eased**3 * target_y)
        set_cursor_position(x, y)
        time.sleep(delay)

    set_cursor_position(target_x, target_y)

def click(x: int = None, y: int = None, button: str = "left", double: bool = False, smooth: bool = True):
    """Effectue un clic de souris contrôlé avec déplacement fluide."""
    if x is not None and y is not None:
        if smooth:
            move_cursor_smooth(x, y)
        else:
            set_cursor_position(x, y)
        time.sleep(0.04)

    cur_x, cur_y = get_cursor_position()

    if button.lower() == "right":
        down_flag, up_flag = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    elif button.lower() == "middle":
        down_flag, up_flag = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
    else:
        down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP

    # Premier clic
    user32.mouse_event(down_flag, cur_x, cur_y, 0, 0)
    time.sleep(0.03)
    user32.mouse_event(up_flag, cur_x, cur_y, 0, 0)

    # Deuxième clic si double-clic
    if double:
        time.sleep(0.08)
        user32.mouse_event(down_flag, cur_x, cur_y, 0, 0)
        time.sleep(0.03)
        user32.mouse_event(up_flag, cur_x, cur_y, 0, 0)

def scroll(amount: int = -3):
    """
    Fait défiler la molette de souris.
    amount positif = haut, négatif = bas.
    """
    cur_x, cur_y = get_cursor_position()
    clicks = amount * 120
    user32.mouse_event(MOUSEEVENTF_WHEEL, cur_x, cur_y, clicks, 0)

def type_text(text: str, delay: float = 0.015):
    """
    Saisit du texte au clavier avec support Unicode complet (accents, ponctuation, etc.).
    """
    for ch in text:
        code = ord(ch)
        user32.keybd_event(0, code, KEYEVENTF_UNICODE, 0)
        time.sleep(0.005)
        user32.keybd_event(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
        if delay > 0:
            time.sleep(delay)

VK_MAP = {
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "escape": 0x1B,
    "esc": 0x1B,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "shift": 0x10,
    "win": 0x5B,
    "windows": 0x5B,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
}

def press_key(key_combo: str):
    """
    Appuie sur une touche ou combinaison de touches (ex: 'ctrl+c', 'enter', 'alt+tab').
    """
    parts = [p.strip().lower() for p in key_combo.split("+")]
    vks = []
    for p in parts:
        if p in VK_MAP:
            vks.append(VK_MAP[p])
        elif len(p) == 1:
            vks.append(ord(p.upper()))

    # Enfoncer dans l'ordre
    for vk in vks:
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.02)

    time.sleep(0.04)

    # Relâcher dans l'ordre inverse
    for vk in reversed(vks):
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.02)
