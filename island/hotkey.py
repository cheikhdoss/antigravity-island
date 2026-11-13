import os
import re
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
    - Synchronisation stricte par jeton de séquence (request_seq) pour annuler immédiatement toute requête obsolète.
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
        self.request_seq = 0  # Compteur séquentiel d'invalidation de requête

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

    def start_manual_recording(self):
        """Démarre l'enregistrement vocal lors d'un clic manuel sur le bouton Island."""
        self.request_seq += 1
        req_id = self.request_seq
        print(f"[PushToTalkEngine] Requête manuelle #{req_id} amorcée.")
        self.window.state_change_requested.emit("stop_reading", {})
        if getattr(self.window, "voice_engine", None):
            self.window.voice_engine.stop()
        self.is_active = True
        self.recorder.start_recording()
        self.window.state_change_requested.emit("set_state", {"state": "listening"})
        return req_id

    def stop_manual_recording(self):
        """Arrête l'enregistrement manuel et passe immédiatement à l'analyse/transcription."""
        if self.is_active:
            self.is_active = False
            self._trigger_thinking_and_capture(self.request_seq)

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
        self.request_seq += 1
        req_id = self.request_seq
        print(f"[PushToTalkEngine] Nouvelle requête #{req_id} amorcée.")

        # Interrompre immédiatement la lecture précédente sur l'Island
        self.window.state_change_requested.emit("stop_reading", {})
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

    def _trigger_thinking_and_capture(self, req_id: int):
        if req_id != self.request_seq:
            return
        # Mode thinking pur : affiche strictement "Analyse en cours..." sans titre parasite
        self.window.state_change_requested.emit("set_state", {"state": "thinking"})
        threading.Thread(target=self._process_voice_and_screen, args=(req_id,), daemon=True).start()

    def _process_voice_and_screen(self, req_id: int):
        if req_id != self.request_seq:
            print(f"[PushToTalk] Requête #{req_id} ignorée (remplacée par #{self.request_seq})")
            return

        appdata_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AntigravityIsland")
        wav_path = os.path.join(appdata_dir, "input_voice.wav")
        query_path = os.path.join(appdata_dir, "last_voice_query.json")

        # 1. Arrêt instantané de l'enregistrement (audio en mémoire vive)
        has_audio = self.recorder.stop_recording(wav_path)
        pcm_bytes = getattr(self.recorder, "last_pcm_bytes", None)
        rms = getattr(self.recorder, "last_rms", 0.0)
        peak = getattr(self.recorder, "last_peak", 0)

        if req_id != self.request_seq:
            print(f"[PushToTalk] Requête #{req_id} annulée après enregistrement audio")
            return

        # 2. Transcription ultra-rapide (<0.2s) directement en mémoire
        transcription = ""
        is_silent = (not has_audio) or (rms < 3.0 and peak < 20)

        is_status_msg = False
        if has_audio and not is_silent:
            try:
                audio_input = pcm_bytes if (pcm_bytes and len(pcm_bytes) > 200) else wav_path
                transcription = transcribe_audio(audio_input)
                if transcription:
                    print(f"[PushToTalk] Requête #{req_id} - Transcription : '{transcription}'")
            except Exception as e:
                print(f"[PushToTalk] Erreur STT #{req_id}:", e)

        if req_id != self.request_seq:
            print(f"[PushToTalk] Requête #{req_id} annulée après transcription")
            return

        # 3. Génération directe de la réponse textuelle (avec streaming en direct)
        accumulated_chunks = []
        def on_stream_chunk(chunk: str):
            if req_id != self.request_seq:
                return
            accumulated_chunks.append(chunk)
            streamed = "".join(accumulated_chunks).strip()
            # Nettoyer les astérisques et balises markdown en cours de frappe
            streamed = re.sub(r'[*_`]', '', streamed)
            if streamed:
                self.window.state_change_requested.emit("stream_text", {"text": streamed})

        if is_silent:
            response_text = "Microphone inaudible. Maintenez Win + Alt et parlez."
            is_status_msg = True
        elif transcription:
            try:
                response_text = generate_response(transcription, on_chunk=on_stream_chunk)
                if not response_text or not response_text.strip():
                    response_text = "Je n'ai pas pu obtenir de réponse. Réessayez."
                    is_status_msg = True
                else:
                    is_status_msg = False
            except Exception as e:
                print(f"[PushToTalk] Exception dans generate_response #{req_id}:", e)
                response_text = "Une erreur est survenue lors de l'analyse."
                is_status_msg = True
        else:
            response_text = "Je n'ai pas bien compris. Parlez un peu plus près du micro."
            is_status_msg = True

        if req_id != self.request_seq:
            print(f"[PushToTalk] Requête #{req_id} annulée avant affichage")
            return

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
        if req_id == self.request_seq:
            self.window.state_change_requested.emit("speak", {
                "text": response_text,
                "is_status": is_status_msg,
                "is_answer": not is_status_msg
            })

    def _handle_combo_up(self, duration: float):
        req_id = self.request_seq
        if self.mode == "hold":
            self.is_active = False
            # Marge affinée à 90ms (au lieu de 280ms) pour capturer la fin naturelle du mot sans latence
            def delayed_capture(r_id):
                time.sleep(0.09)
                if r_id == self.request_seq:
                    self._trigger_thinking_and_capture(r_id)
            threading.Thread(target=delayed_capture, args=(req_id,), daemon=True).start()
        elif self.mode == "toggle":
            if not self.is_active:
                self.is_active = True
                self.recorder.start_recording()
                self.window.state_change_requested.emit("set_state", {"state": "listening"})
            else:
                self.is_active = False
                self._trigger_thinking_and_capture(req_id)
        else:  # hybrid
            if duration >= 0.15:
                self.is_active = False
                def delayed_capture(r_id):
                    time.sleep(0.09)
                    if r_id == self.request_seq:
                        self._trigger_thinking_and_capture(r_id)
                threading.Thread(target=delayed_capture, args=(req_id,), daemon=True).start()
            else:
                # Tap court (<150ms) : bascule mains-libres
                if not self.is_active:
                    self.is_active = True
                else:
                    self.is_active = False
                    self._trigger_thinking_and_capture(req_id)
