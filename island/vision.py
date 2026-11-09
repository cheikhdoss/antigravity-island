import os
import time
import mss
import mss.tools

def get_screenshot_dir():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = os.path.expanduser("~")
    shot_dir = os.path.join(appdata, "AntigravityIsland", "screenshots")
    os.makedirs(shot_dir, exist_ok=True)
    return shot_dir

def capture_screen(monitor_index: int = 1, filename: str = None) -> dict:
    """
    Capture instantanée de l'écran avec le moteur haute performance MSS.
    Retourne le chemin d'accès absolu au fichier PNG, la largeur et la hauteur.
    """
    try:
        shot_dir = get_screenshot_dir()
        if not filename:
            filename = f"screen_{int(time.time())}.png"
        
        output_path = os.path.join(shot_dir, filename)
        latest_path = os.path.join(shot_dir, "screen_latest.png")

        with mss.MSS() as sct:
            if monitor_index < len(sct.monitors):
                monitor = sct.monitors[monitor_index]
            else:
                monitor = sct.monitors[0]

            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=output_path)
            
            # Duplication vers screen_latest.png pour accès direct permanent
            try:
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=latest_path)
            except Exception:
                pass

        return {
            "status": "success",
            "file_path": output_path,
            "latest_path": latest_path,
            "width": monitor["width"],
            "height": monitor["height"],
            "left": monitor["left"],
            "top": monitor["top"],
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def get_screens_info() -> dict:
    """Retourne la géométrie de tous les écrans connectés."""
    try:
        with mss.MSS() as sct:
            return {
                "status": "success",
                "monitors": sct.monitors
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}
