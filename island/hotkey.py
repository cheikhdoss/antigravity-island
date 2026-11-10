import os
import json
import time
import threading
from pynput import keyboard
from island.audio_recorder import AudioRecorder
from island.stt import transcribe_audio
from island.brain import generate_response

class PushToTalkEngine:
    """
    Moteur Push-to-Talk global avec combinaison de touches Windows + Alt.
    Détecte les touches n'importe où sous Windows, même si l'application est en arrière-plan.
    Supporte les modes Hybride (recommandé), Maintien (Hold) et Bascule (Toggle).
    Enregistre le micro, transcrit la voix et génère une réponse instantanée affichée sur l'encoche.
    """

    def __init__(self, window_instance, mode: str = "hybrid"):
        self.window = window_instance
        self.mode = mode
        self.listener = None
        self.running = False
        self.recorder = AudioRecorder()
        
        self.win_pressed = False
        self.alt_pressed = False
        self.press_start_time = 0.0
        self.is_active = False
        self._lock = threading.Lock()

    def start(self):
        if self.running:
            return
        self.running = True
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.daemon = True
        self.listener.start()
        print("[PushToTalkEngine] Raccourci global actif : [Windows + Alt]")

    def stop(self):
        self.running = False
        if self.listener:
            self.listener.stop()
            self.listener = None

    def set_mode(self, mode: str):
        self.mode = mode

    def _is_win_key(self, key):
        return key in [keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r]

    def _is_alt_key(self, key):
        return key in [keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr]

    def _on_press(self, key):
        with self._lock:
            if self._is_win_key(key):
                self.win_pressed = True
            elif self._is_alt_key(key):
                self.alt_pressed = True

            # Détection de la combinaison Windows + Alt
            if self.win_pressed and self.alt_pressed:
                if self.press_start_time == 0.0:
                    self.press_start_time = time.time()
                    self._handle_combo_down()

    def _on_release(self, key):
        with self._lock:
            was_combo_active = self.win_pressed and self.alt_pressed
            
            if self._is_win_key(key):
                self.win_pressed = False
            elif self._is_alt_key(key):
                self.alt_pressed = False

            # Relâchement de l'une des touches
            if was_combo_active and not (self.win_pressed and self.alt_pressed):
                press_duration = time.time() - self.press_start_time
                self.press_start_time = 0.0
                self._handle_combo_up(press_duration)

    def _handle_combo_down(self):
        if self.mode == "hold":
            self.is_active = True
            print("[PushToTalk] Maintien [Windows + Alt] -> Mode Ecoute...")
            self.recorder.start_recording()
            self.window.state_change_requested.emit("set_state", {"state": "listening"})
        elif self.mode == "toggle":
            # Géré au relâchement
            pass
        else:  # hybrid
            if not self.is_active:
                print("[PushToTalk] Combinaison [Windows + Alt] -> Demarrage ecoute...")
                self.recorder.start_recording()
                self.window.state_change_requested.emit("set_state", {"state": "listening"})
            else:
                # Déjà actif : ne PAS réinitialiser l'enregistrement
                pass

    def _trigger_thinking_and_capture(self):
        self.window.state_change_requested.emit("set_state", {"state": "thinking"})
        threading.Thread(target=self._process_voice_and_screen, daemon=True).start()

    def _process_voice_and_screen(self):
        appdata_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AntigravityIsland")
        wav_path = os.path.join(appdata_dir, "input_voice.wav")
        query_path = os.path.join(appdata_dir, "last_voice_query.json")

        # 1. Arrêt de l'enregistrement et sauvegarde audio
        has_audio = self.recorder.stop_recording(wav_path)
        rms = getattr(self.recorder, "last_rms", 0.0)
        peak = getattr(self.recorder, "last_peak", 0)

        # 2. Transcription vocale native Windows
        transcription = ""
        is_silent = (not has_audio) or (rms < 3.0 and peak < 20)

        if has_audio and not is_silent:
            try:
                transcription = transcribe_audio(wav_path)
                if transcription:
                    print(f"[PushToTalk] Transcription : '{transcription}'")
            except Exception as e:
                print("[PushToTalk] Erreur STT:", e)

        # 3. Génération de la réponse conversationnelle
        if is_silent:
            response_text = "Microphone inaudible. Vérifiez la touche micro (F4) et parlez."
        elif transcription:
            response_text = generate_response(transcription)
        else:
            response_text = "Je n'ai pas bien compris. Parlez un peu plus fort ou plus près du micro."

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

        # 5. Réponse affichée directement sur l'encoche
        self.window.state_change_requested.emit("speak", {"text": response_text})
        
        # Maintien de l'affichage de la réponse (5.0s) avant retour fluide au repos
        time.sleep(5.0)
        self.window.state_change_requested.emit("set_state", {"state": "idle"})

    def _handle_combo_up(self, duration: float):
        if self.mode == "hold":
            self.is_active = False
            print(f"[PushToTalk] Relachement apres {duration:.2f}s -> Passage en Analyse...")
            self._trigger_thinking_and_capture()
        elif self.mode == "toggle":
            if not self.is_active:
                self.is_active = True
                print("[PushToTalk] Bascule on -> Mode Ecoute...")
                self.recorder.start_recording()
                self.window.state_change_requested.emit("set_state", {"state": "listening"})
            else:
                self.is_active = False
                print("[PushToTalk] Bascule off -> Passage en Analyse...")
                self._trigger_thinking_and_capture()
        else:  # hybrid
            if duration >= 0.35:
                # Maintien long : Push-to-Talk classique (on relâche pour envoyer)
                self.is_active = False
                print(f"[PushToTalk] Relachement maintien ({duration:.2f}s) -> Analyse...")
                self._trigger_thinking_and_capture()
            else:
                # Tap court : bascule mains-libres
                if not self.is_active:
                    self.is_active = True
                    print("[PushToTalk] Tap court -> Mode Mains-libres active (re-tapez Win+Alt pour arreter)...")
                    # L'enregistrement a déjà démarré dans _handle_combo_down
                else:
                    self.is_active = False
                    print("[PushToTalk] Second tap court -> Fin d'ecoute mains-libres, Analyse...")
                    self._trigger_thinking_and_capture()
