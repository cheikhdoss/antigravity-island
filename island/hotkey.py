import os
import json
import time
import threading
import ctypes
from island.audio_recorder import AudioRecorder
from island.stt import transcribe_audio
from island.brain import generate_response

user32 = ctypes.windll.user32
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_MENU = 0x12  # Alt

def is_key_physically_down(vk: int) -> bool:
    """Interroge directement l'état matériel du noyau Windows (impossible de rester bloqué)."""
    return (user32.GetAsyncKeyState(vk) & 0x8000) != 0

class PushToTalkEngine:
    """
    Moteur Push-to-Talk matériel ultra-robuste avec combinaison [Windows + Alt].
    - Utilise GetAsyncKeyState du noyau Windows : aucune désynchronisation possible, aucun conflit avec Alt+Tab.
    - Démarrage instantané et arrêt immédiat.
    - Enregistre le micro, transcrit la voix et génère une réponse instantanée affichée sur l'encoche.
    """

    def __init__(self, window_instance, mode: str = "hold"):
        self.window = window_instance
        self.mode = mode
        self.running = False
        self.thread = None
        self.recorder = AudioRecorder()
        
        self.combo_active = False
        self.press_start_time = 0.0
        self.is_active = False

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        print("[PushToTalkEngine] Raccourci matériel actif : [Windows + Alt] (GetAsyncKeyState)")

    def stop(self):
        self.running = False

    def set_mode(self, mode: str):
        self.mode = mode

    def _poll_loop(self):
        while self.running:
            time.sleep(0.02)  # 50 Hz : ultra-réactif (20ms) et 0.00% CPU
            try:
                win_down = is_key_physically_down(VK_LWIN) or is_key_physically_down(VK_RWIN)
                alt_down = is_key_physically_down(VK_MENU)
                combo_down = win_down and alt_down

                if combo_down and not self.combo_active:
                    # Début de combinaison
                    self.combo_active = True
                    self.press_start_time = time.time()
                    self._handle_combo_down()
                elif not combo_down and self.combo_active:
                    # Fin de combinaison
                    self.combo_active = False
                    duration = time.time() - self.press_start_time
                    self.press_start_time = 0.0
                    self._handle_combo_up(duration)
            except Exception:
                pass

    def _handle_combo_down(self):
        if getattr(self.window, "voice_engine", None):
            self.window.voice_engine.stop()

        if self.mode == "hold":
            self.is_active = True
            self.recorder.start_recording()
            self.window.state_change_requested.emit("set_state", {"state": "listening"})
        elif self.mode == "toggle":
            pass
        else:  # hybrid
            if not self.is_active:
                self.recorder.start_recording()
                self.window.state_change_requested.emit("set_state", {"state": "listening"})

    def _trigger_thinking_and_capture(self):
        self.window.state_change_requested.emit("set_state", {"state": "thinking"})
        threading.Thread(target=self._process_voice_and_screen, daemon=True).start()

    def _process_voice_and_screen(self):
        appdata_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AntigravityIsland")
        wav_path = os.path.join(appdata_dir, "input_voice.wav")
        query_path = os.path.join(appdata_dir, "last_voice_query.json")

        # 1. Arrêt instantané de l'enregistrement
        has_audio = self.recorder.stop_recording(wav_path)
        rms = getattr(self.recorder, "last_rms", 0.0)
        peak = getattr(self.recorder, "last_peak", 0)

        # 2. Transcription ultra-rapide (<0.4s)
        transcription = ""
        is_silent = (not has_audio) or (rms < 3.0 and peak < 20)

        if has_audio and not is_silent:
            try:
                transcription = transcribe_audio(wav_path)
                if transcription:
                    print(f"[PushToTalk] Transcription : '{transcription}'")
            except Exception as e:
                print("[PushToTalk] Erreur STT:", e)

        # 3. Génération directe de la réponse textuelle (avec streaming en direct)
        accumulated_chunks = []
        def on_stream_chunk(chunk: str):
            accumulated_chunks.append(chunk)
            streamed = "".join(accumulated_chunks).strip()
            if streamed:
                self.window.state_change_requested.emit("stream_text", {"text": streamed})

        if is_silent:
            response_text = "Microphone inaudible. Maintenez Win + Alt et parlez."
        elif transcription:
            response_text = generate_response(transcription, on_chunk=on_stream_chunk)
        else:
            response_text = "Je n'ai pas bien compris. Parlez un peu plus près du micro."

        # 4. Sauvegarde de la requête et de la réponse
        payload = {
            "timestamp": time.time(),
            "query": transcription,
            "response": response_text,
            "has_audio": has_audio,
            "rms": rms,
            "peak": peak,
            "wav_path": wav_path if has_audio else None
        }
        try:
            with open(query_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # 5. Affichage direct et instantané sur le Dynamic Island (sans voix)
        self.window.state_change_requested.emit("speak", {"text": response_text})

    def _handle_combo_up(self, duration: float):
        if self.mode == "hold":
            self.is_active = False
            self._trigger_thinking_and_capture()
        elif self.mode == "toggle":
            if not self.is_active:
                self.is_active = True
                self.recorder.start_recording()
                self.window.state_change_requested.emit("set_state", {"state": "listening"})
            else:
                self.is_active = False
                self._trigger_thinking_and_capture()
        else:  # hybrid
            if duration >= 0.15:
                # Maintien classique Push-to-Talk : déclenchement immédiat dès relâchement
                self.is_active = False
                self._trigger_thinking_and_capture()
            else:
                # Tap court (<150ms) : bascule mains-libres
                if not self.is_active:
                    self.is_active = True
                else:
                    self.is_active = False
                    self._trigger_thinking_and_capture()
