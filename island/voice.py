import os
import time
import asyncio
import threading
import ctypes
import math

try:
    import edge_tts
    HAS_EDGE_TTS = True
except Exception:
    HAS_EDGE_TTS = False

class VoiceEngine:
    """
    Moteur de synthèse vocale haute fidélité utilisant Edge-TTS (voix neuronales naturelles Microsoft).
    Produit une voix humaine fluide, rapide et expressive en français, sans aucun robotisme SAPI.
    Anime simultanément la waveform de l'encoche et gère le retour fluide à l'état de repos.
    """

    DEFAULT_VOICE = "fr-FR-VivienneMultilingualNeural"
    DEFAULT_RATE = "+10%"

    def __init__(self, window_instance=None, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE):
        self.window = window_instance
        self.voice = voice
        self.rate = rate
        self.enabled = True
        self.winmm = ctypes.windll.winmm
        self.alias = "island_edge_tts"
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._current_thread = None

        self.cache_dir = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            "AntigravityIsland",
            "tts_cache"
        )
        os.makedirs(self.cache_dir, exist_ok=True)

    def set_voice(self, voice_name: str):
        self.voice = voice_name

    def set_rate(self, rate_str: str):
        self.rate = rate_str

    def stop(self):
        """Arrête immédiatement toute lecture audio en cours."""
        self._stop_event.set()
        try:
            self.winmm.mciSendStringW(f"stop {self.alias}", None, 0, None)
            self.winmm.mciSendStringW(f"close {self.alias}", None, 0, None)
        except Exception:
            pass

    def speak(self, text: str, callback_on_finish=None):
        """Synthétise et prononce le texte en arrière-plan avec Edge-TTS."""
        if not text or not text.strip():
            if callback_on_finish:
                callback_on_finish()
            return

        self.stop()
        self._stop_event.clear()

        thread = threading.Thread(
            target=self._speak_worker,
            args=(text.strip(), callback_on_finish),
            daemon=True
        )
        self._current_thread = thread
        thread.start()

    def _speak_worker(self, text: str, callback_on_finish=None):
        with self._lock:
            # Nettoyer d'anciens MP3
            mp3_path = os.path.join(self.cache_dir, f"speech_{int(time.time()*1000)}.mp3")

            # 1. Génération audio via Edge-TTS
            success = False
            if HAS_EDGE_TTS:
                try:
                    async def _gen():
                        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
                        await communicate.save(mp3_path)
                    asyncio.run(_gen())
                    success = os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 100
                except Exception as e:
                    print(f"[VoiceEngine] Erreur Edge-TTS : {e}")

            if not success or self._stop_event.is_set():
                if callback_on_finish:
                    try: callback_on_finish()
                    except Exception: pass
                return

            # 2. Lecture audio native fluide via MCI mpegvideo
            try:
                abs_path = os.path.abspath(mp3_path)
                self.winmm.mciSendStringW(f"close {self.alias}", None, 0, None)
                open_res = self.winmm.mciSendStringW(f'open "{abs_path}" type mpegvideo alias {self.alias}', None, 0, None)
                if open_res != 0:
                    print(f"[VoiceEngine] MCI open failed : {open_res}")
                    return

                self.winmm.mciSendStringW(f"play {self.alias}", None, 0, None)

                # Animation dynamique de la waveform pendant la lecture
                buf = ctypes.create_unicode_buffer(64)
                t = 0.0
                while not self._stop_event.is_set():
                    self.winmm.mciSendStringW(f"status {self.alias} mode", buf, 64, None)
                    mode = buf.value
                    if mode != "playing":
                        break
                    
                    # Pulsation naturelle pour la waveform de l'encoche
                    pulse = 0.35 + 0.55 * abs(math.sin(t * 7.5))
                    if self.window:
                        self.window.audio_power = pulse

                    time.sleep(0.04)
                    t += 0.04

                self.winmm.mciSendStringW(f"close {self.alias}", None, 0, None)

            except Exception as e:
                print(f"[VoiceEngine] Erreur lecture : {e}")
            finally:
                if self.window:
                    self.window.audio_power = 0.0
                try:
                    if os.path.exists(mp3_path):
                        os.remove(mp3_path)
                except Exception:
                    pass

            if callback_on_finish and not self._stop_event.is_set():
                try:
                    callback_on_finish()
                except Exception:
                    pass
