import ctypes
import time
import os

winmm = ctypes.windll.winmm
out = os.path.abspath(r"C:\Users\pro\.gemini\antigravity\scratch\antigravity-island\scratch\test_tts.mp3")
alias = "test_tts_alias"

winmm.mciSendStringW(f"close {alias}", None, 0, None)
r1 = winmm.mciSendStringW(f'open "{out}" type mpegvideo alias {alias}', None, 0, None)
r2 = winmm.mciSendStringW(f"play {alias}", None, 0, None)
print("Open res:", r1, "Play res:", r2)

# Query length
buf = ctypes.create_unicode_buffer(128)
winmm.mciSendStringW(f"set {alias} time format ms", None, 0, None)
winmm.mciSendStringW(f"status {alias} length", buf, 128, None)
print("Length (ms):", buf.value)

# Query mode while playing
for _ in range(15):
    winmm.mciSendStringW(f"status {alias} mode", buf, 128, None)
    mode = buf.value
    if mode != "playing":
        break
    time.sleep(0.2)

winmm.mciSendStringW(f"close {alias}", None, 0, None)
print("Done playback!")
