import threading
import time
import win32com.client

class VoiceEngine:
    """
    Moteur de synthèse vocale natif Windows (SAPI5).
    Utilise la voix française intégrée (Microsoft Hortense) sans dépendance tierce.
    """
    def __init__(self, window_instance=None):
        self.window = window_instance
        self.enabled = True
        self.speaker = None
        self._lock = threading.Lock()
        self._speaking_thread = None
        self._init_speaker()

    def _init_speaker(self):
        try:
            self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
            voices = self.speaker.GetVoices()
            for i in range(voices.Count):
                desc = voices.Item(i).GetDescription().lower()
                if "french" in desc or "hortense" in desc:
                    self.speaker.Voice = voices.Item(i)
                    break
        except Exception as e:
            print("[VoiceEngine] Erreur initialisation SAPI:", e)

    def speak(self, text: str, callback_on_finish=None):
        """Prononce le texte de manière asynchrone et anime l'encoche."""
        if not self.enabled or not text.strip():
            if callback_on_finish:
                callback_on_finish()
            return

        thread = threading.Thread(target=self._speak_worker, args=(text, callback_on_finish), daemon=True)
        thread.start()

    def _speak_worker(self, text: str, callback_on_finish=None):
        with self._lock:
            try:
                # Ré-instancier pour le thread COM
                import pythoncom
                pythoncom.CoInitialize()
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                voices = speaker.GetVoices()
                for i in range(voices.Count):
                    desc = voices.Item(i).GetDescription().lower()
                    if "french" in desc or "hortense" in desc:
                        speaker.Voice = voices.Item(i)
                        break

                # Animation de la waveform pendant la parole
                stop_wave = threading.Event()
                def wave_pulse():
                    import math
                    t = 0.0
                    while not stop_wave.is_set():
                        power = 0.4 + 0.5 * abs(math.sin(t * 8.0))
                        if self.window:
                            self.window.audio_power = power
                        time.sleep(0.05)
                        t += 0.05

                wave_thread = threading.Thread(target=wave_pulse, daemon=True)
                wave_thread.start()

                # Prononciation synchrone dans ce thread dédié
                speaker.Speak(text)

                stop_wave.set()
                if self.window:
                    self.window.audio_power = 0.0

            except Exception as e:
                print("[VoiceEngine] Erreur de lecture audio:", e)
            finally:
                pythoncom.CoUninitialize()

            # Callback fin de parole (ex: retour à l'état idle après 1 seconde)
            if callback_on_finish:
                try:
                    callback_on_finish()
                except Exception:
                    pass
