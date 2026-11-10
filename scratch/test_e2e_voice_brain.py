import sys
import os
import time

sys.path.insert(0, r"C:\Users\pro\.gemini\antigravity\scratch\antigravity-island")

from island.brain import generate_response
from island.voice import VoiceEngine

class DummyWindow:
    def __init__(self):
        self.audio_power = 0.0

def test():
    win = DummyWindow()
    engine = VoiceEngine(window_instance=win)

    # Test 1: Salutation rapide
    print("\n--- Test 1: Salutation rapide ---")
    resp1 = generate_response("Bonjour Antigravity")
    print("Reponse 1:", resp1)
    
    done = [False]
    def on_finish():
        done[0] = True
        print("\n[Voix] Lecture terminee !")

    print("[Voix] Debut prononciation Test 1...")
    engine.speak(resp1, callback_on_finish=on_finish)
    
    # Attendre la fin
    for _ in range(100):
        if done[0]: break
        time.sleep(0.1)

    print("\nTest 1 valide !")

if __name__ == "__main__":
    test()
