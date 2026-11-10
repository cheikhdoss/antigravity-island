import asyncio
import os
import time
import ctypes
import edge_tts

VOICE = "fr-FR-HenriNeural"
OUTPUT_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AntigravityIsland")
TTS_FILE = os.path.join(OUTPUT_DIR, "output_speech.mp3")

async def generate_speech(text: str, voice: str = VOICE, output_path: str = TTS_FILE) -> bool:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except Exception:
            pass
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 100
    except Exception as e:
        print("[TTS] Erreur generation speech:", e)
        return False

def play_audio(mp3_path: str, on_tick=None) -> bool:
    winmm = ctypes.windll.winmm
    alias = "island_edge_tts"
    abs_path = os.path.abspath(mp3_path)
    
    try:
        winmm.mciSendStringW(f"close {alias}", None, 0, None)
        r_open = winmm.mciSendStringW(f'open "{abs_path}" type mpegvideo alias {alias}', None, 0, None)
        if r_open != 0:
            print("[TTS] Echec ouverture MCI:", r_open)
            return False

        winmm.mciSendStringW(f"play {alias}", None, 0, None)

        buf = ctypes.create_unicode_buffer(64)
        while True:
            winmm.mciSendStringW(f"status {alias} mode", buf, 64, None)
            mode = buf.value
            if mode != "playing":
                break
            if on_tick:
                on_tick()
            time.sleep(0.1)

        winmm.mciSendStringW(f"close {alias}", None, 0, None)
        return True
    except Exception as e:
        print("[TTS] Erreur lecture audio:", e)
        try:
            winmm.mciSendStringW(f"close {alias}", None, 0, None)
        except Exception:
            pass
        return False

if __name__ == "__main__":
    t0 = time.time()
    text = "Bonjour ! Je suis Antigravity Island, votre compagnon intelligent."
    print("Generating speech...")
    asyncio.run(generate_speech(text))
    print(f"Generated in {time.time() - t0:.2f}s! Playing...")
    play_audio(TTS_FILE, on_tick=lambda: print(".", end="", flush=True))
    print("\nPlayback complete in total", time.time() - t0, "s")
