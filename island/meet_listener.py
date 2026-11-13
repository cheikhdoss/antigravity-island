import os
import time
import queue
import threading
import numpy as np
import collections
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

try:
    import pyaudiowpatch as pyaudio
    HAS_PYAUDIO_WPATCH = True
except Exception:
    HAS_PYAUDIO_WPATCH = False

from island.stt import transcribe_audio, transcribe_audio_google

# Liste complète des déclencheurs interrogatifs fréquents en cours / réunion Meet
MEET_QUESTION_TRIGGERS = [
    # Déclencheurs explicites demandés par l'utilisateur
    "c'est quoi", "c est quoi", "cest quoi",
    "pourquoi dit-on", "pourquoi dit on", "pourquoi dit-ton", "pourquoi dit ton",
    "qu'est-ce que", "qu est ce que", "quest ce que", "qu'est ce que",
    "qu'est-ce qui", "qu'est ce qui", "quest ce qui", "qu est ce qui",
    "quelle est", "quel est", "quels sont", "quelles sont",
    # Variantes interrogatives et questions directes du professeur
    "pourquoi",
    "comment", "comment on", "comment fait-on", "comment fait on", "comment fonctionne",
    "qui peut me dire", "qui peut nous dire", "qui sait", "qui peut répondre",
    "qui a une idée", "qui a une idee", "qui se rappelle", "qui se souvient",
    "quelqu'un peut", "quelqu'un sait", "quelqu un peut", "quelqu un sait",
    "que signifie", "que veut dire", "qu'est-ce que cela signifie", "qu'entend-on par", "qu entend on par",
    "à quoi sert", "a quoi sert", "ça sert à quoi", "ca sert a quoi",
    "en quoi consiste", "c'est-à-dire", "c est a dire",
    "combien de", "combien d'", "combien d",
    "savez-vous", "savez vous", "est-ce que vous savez", "est ce que vous savez",
    "d'après vous", "d apres vous", "selon vous", "à votre avis", "a votre avis",
    "donnez-moi", "donnez moi", "citez-moi", "citez moi", "donnez un exemple",
    "expliquez", "expliquez-moi", "expliquez moi", "expliquez pourquoi",
    "peut-on", "peut on", "est-ce que", "est ce que",
    "lequel", "laquelle", "lesquels", "lesquelles",
    "vrai ou faux", "c'est vrai ou faux", "quelle option", "quelle réponse",
    "qu'en pensez-vous", "qu en pensez vous", "quelle différence", "quelle est la différence"
]

def is_teacher_question(text: str) -> bool:
    """Détecte avec précision si une phrase transcrite est une question posée par le professeur."""
    if not text:
        return False
    norm = text.lower().strip()
    if len(norm) < 4:
        return False

    # 1. Termine par un point d'interrogation
    if norm.endswith("?"):
        return True

    # 2. Contient l'un des déclencheurs ciblés
    for trig in MEET_QUESTION_TRIGGERS:
        if trig in norm:
            return True

    # 3. Mots interrogatifs en début de phrase
    tokens = norm.replace("?", "").replace(",", "").replace(".", "").split()
    if tokens and tokens[0] in [
        "pourquoi", "comment", "combien", "qui", "lequel", "laquelle",
        "lesquels", "lesquelles", "qu'est-ce", "que", "quoi", "où", "ou", "est-ce"
    ]:
        return True

    return False

def convert_loopback_to_16k_mono(raw_pcm: bytes, orig_channels: int, orig_rate: int) -> bytes:
    """Convertit un bloc audio loopback (généralement 48kHz stéréo) en 16kHz mono 16-bit PCM de haute fidélité."""
    try:
        samples = np.frombuffer(raw_pcm, dtype=np.int16)
        if len(samples) == 0:
            return b""

        # 1. Passage en mono
        if orig_channels == 2:
            samples = samples.reshape(-1, 2).mean(axis=1).astype(np.int16)
        elif orig_channels > 2:
            samples = samples.reshape(-1, orig_channels)[:, 0].astype(np.int16)

        # 2. Ré-échantillonnage vers 16000 Hz
        if orig_rate == 48000:
            # 48kHz -> 16kHz : filtrage anti-aliasing parfait par moyenne sur facteur 3
            trim = (len(samples) // 3) * 3
            if trim > 0:
                samples = samples[:trim].reshape(-1, 3).mean(axis=1).astype(np.int16)
            else:
                return b""
        elif orig_rate != 16000 and len(samples) > 0:
            target_len = int(len(samples) * 16000 / orig_rate)
            if target_len > 0:
                indices = np.linspace(0, len(samples) - 1, target_len)
                samples = np.interp(indices, np.arange(len(samples)), samples).astype(np.int16)

        return samples.tobytes()
    except Exception as e:
        print("[MeetListener] Erreur conversion audio loopback:", e)
        return b""

class MeetListener(QObject):
    """
    Écouteur hybride temps réel pour cours et réunions en direct (Meet, Teams, Zoom, Amphi).
    - Capture en continu le flux des haut-parleurs/écouteurs (WASAPI Loopback) pour la voix du prof distant.
    - Capture simultanément le flux du microphone local pour les simulations de l'étudiant ou les cours en présentiel.
    - Analyse par VAD (Voice Activity Detection), réassemble les phrases et filtre spécifiquement les questions.
    - Déclenche instantanément la capture d'écran de la présentation et l'analyse multimodale par l'IA.
    """
    status_changed = pyqtSignal(bool)
    question_detected = pyqtSignal(str)
    speech_transcribed = pyqtSignal(str, bool)  # text, is_question
    rms_updated = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Seuils acoustiques VAD
        self.mic_energy_threshold = 80.0    # RMS minimum pour considérer la voix micro
        self.loop_energy_threshold = 50.0   # RMS minimum pour considérer le son haut-parleurs
        self.silence_timeout = 1.0          # Secondes de silence pour finaliser la phrase
        self.max_phrase_duration = 10.0     # Durée maximale par phrase
        self.min_speech_duration = 0.55     # Durée minimale pour éliminer les clics

        self.mic_queue = queue.Queue(maxsize=150)
        self.loop_queue = queue.Queue(maxsize=150)
        self.loop_channels = 2
        self.loop_rate = 48000

    def toggle(self) -> bool:
        if self.is_running:
            self.stop()
            return False
        else:
            self.start()
            return True

    def start(self):
        if self.is_running:
            return
        if not HAS_PYAUDIO_WPATCH:
            print("[MeetListener] pyaudiowpatch non disponible. Impossible d'activer le mode Meet.")
            return

        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_dual_audio_loop, daemon=True)
        self._thread.start()
        self.status_changed.emit(True)
        print("[MeetListener] Mode Meet ACTIVÉ : écoute continue hybride (Haut-parleurs Loopback + Microphone).")

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None
        self.status_changed.emit(False)
        print("[MeetListener] Mode Meet DÉSACTIVÉ.")

    def _mic_stream_callback(self, in_data, frame_count, time_info, status):
        """Callback non-bloquant de capture microphone (16kHz mono)."""
        try:
            samples = np.frombuffer(in_data, dtype=np.int16)
            rms = float(np.sqrt(np.mean(samples.astype(np.float64)**2))) if len(samples) > 0 else 0.0
            if not self.mic_queue.full():
                self.mic_queue.put_nowait((in_data, rms, time.time()))
        except Exception:
            pass
        return (None, pyaudio.paContinue)

    def _loop_stream_callback(self, in_data, frame_count, time_info, status):
        """Callback non-bloquant de capture loopback haut-parleurs (WASAPI Loopback)."""
        try:
            samples = np.frombuffer(in_data, dtype=np.int16)
            rms = float(np.sqrt(np.mean(samples.astype(np.float64)**2))) if len(samples) > 0 else 0.0
            mono_16k = convert_loopback_to_16k_mono(in_data, self.loop_channels, self.loop_rate)
            if not self.loop_queue.full():
                self.loop_queue.put_nowait((mono_16k, rms, time.time()))
        except Exception:
            pass
        return (None, pyaudio.paContinue)

    def _run_dual_audio_loop(self):
        """Boucle d'écoute double canal (Microphone + Haut-parleurs Loopback) ultra-réactive."""
        pa = None
        stream_loop = None
        stream_mic = None

        while not self.mic_queue.empty():
            try: self.mic_queue.get_nowait()
            except Exception: break
        while not self.loop_queue.empty():
            try: self.loop_queue.get_nowait()
            except Exception: break

        try:
            pa = pyaudio.PyAudio()

            # 1. Configuration du flux Loopback (Haut-parleurs)
            loop_device = None
            try:
                wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
                default_speakers = pa.get_device_info_by_index(wasapi_info['defaultOutputDevice'])
                if default_speakers.get('isLoopbackDevice', False):
                    loop_device = default_speakers
                else:
                    for l in pa.get_loopback_device_info_generator():
                        if default_speakers['name'] in l['name']:
                            loop_device = l
                            break
                if not loop_device:
                    for l in pa.get_loopback_device_info_generator():
                        loop_device = l
                        break
            except Exception as e_dev:
                print("[MeetListener] Détection loopback:", e_dev)

            if loop_device:
                self.loop_rate = int(loop_device['defaultSampleRate'])
                self.loop_channels = int(loop_device['maxInputChannels'])
                try:
                    stream_loop = pa.open(
                        format=pyaudio.paInt16,
                        channels=self.loop_channels,
                        rate=self.loop_rate,
                        frames_per_buffer=1024,
                        input=True,
                        input_device_index=loop_device['index'],
                        stream_callback=self._loop_stream_callback
                    )
                    stream_loop.start_stream()
                    print(f"[MeetListener] Canal Loopback actif : {loop_device['name']} ({self.loop_rate}Hz, {self.loop_channels}ch)")
                except Exception as e_s:
                    print("[MeetListener] Impossible d'ouvrir le flux Loopback :", e_s)
                    stream_loop = None

            # 2. Configuration du flux Microphone
            try:
                mic_device = pa.get_default_input_device_info()
                stream_mic = pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    frames_per_buffer=1024,
                    input=True,
                    input_device_index=mic_device['index'],
                    stream_callback=self._mic_stream_callback
                )
                stream_mic.start_stream()
                print(f"[MeetListener] Canal Microphone actif : {mic_device['name']} (16000Hz, mono)")
            except Exception as e_m:
                print("[MeetListener] Impossible d'ouvrir le flux Microphone :", e_m)
                stream_mic = None

            if not stream_loop and not stream_mic:
                print("[MeetListener] Aucun canal audio disponible. Arrêt.")
                self.is_running = False
                self.status_changed.emit(False)
                return

            # Ring buffer de pré-capture (environ 300ms) pour ne jamais couper le premier mot
            pre_buffer = collections.deque(maxlen=6)
            accumulated_chunks = []
            is_speaking = False
            last_speech_time = 0.0
            phrase_start_time = 0.0
            active_source = "none"

            # 3. Boucle de coordination VAD
            while not self._stop_event.is_set():
                time.sleep(0.02)
                now = time.time()

                # Vider les queues et récupérer les derniers chunks
                latest_mic_chunk = None
                latest_mic_rms = 0.0
                while not self.mic_queue.empty():
                    try:
                        data_m, rms_m, t_m = self.mic_queue.get_nowait()
                        latest_mic_chunk = data_m
                        if rms_m > latest_mic_rms:
                            latest_mic_rms = rms_m
                    except Exception:
                        break

                latest_loop_chunk = None
                latest_loop_rms = 0.0
                while not self.loop_queue.empty():
                    try:
                        data_l, rms_l, t_l = self.loop_queue.get_nowait()
                        latest_loop_chunk = data_l
                        if rms_l > latest_loop_rms:
                            latest_loop_rms = rms_l
                    except Exception:
                        break

                # Choix de la source prioritaire
                has_loop_speech = (latest_loop_rms >= self.loop_energy_threshold and latest_loop_chunk is not None)
                has_mic_speech = (latest_mic_rms >= self.mic_energy_threshold and latest_mic_chunk is not None)

                chosen_chunk = None
                max_rms = max(latest_loop_rms, latest_mic_rms)
                self.rms_updated.emit(max_rms)

                if has_loop_speech:
                    chosen_chunk = latest_loop_chunk
                    active_source = "Haut-parleurs (Meet)"
                elif has_mic_speech:
                    chosen_chunk = latest_mic_chunk
                    active_source = "Microphone (Local)"
                elif latest_mic_chunk is not None:
                    chosen_chunk = latest_mic_chunk
                elif latest_loop_chunk is not None:
                    chosen_chunk = latest_loop_chunk

                speech_active = has_loop_speech or has_mic_speech

                if speech_active:
                    if not is_speaking:
                        is_speaking = True
                        phrase_start_time = now
                        accumulated_chunks = list(pre_buffer)
                        print(f"[MeetListener] 🎙️ Début de parole détecté via {active_source} (RMS={max_rms:.1f})")
                    last_speech_time = now
                    if chosen_chunk:
                        accumulated_chunks.append(chosen_chunk)
                else:
                    if chosen_chunk:
                        pre_buffer.append(chosen_chunk)

                    if is_speaking:
                        # Append trailing chunk
                        if chosen_chunk:
                            accumulated_chunks.append(chosen_chunk)
                        
                        silence_dur = now - last_speech_time
                        phrase_dur = now - phrase_start_time

                        if silence_dur >= self.silence_timeout or phrase_dur >= self.max_phrase_duration:
                            is_speaking = False
                            if phrase_dur >= self.min_speech_duration and len(accumulated_chunks) > 0:
                                pcm_full = b"".join(accumulated_chunks)
                                accumulated_chunks = []
                                print(f"[MeetListener] Phrase capturée ({phrase_dur:.1f}s, {len(pcm_full)} octets via {active_source}). Analyse STT...")
                                threading.Thread(
                                    target=self._process_speech_chunk,
                                    args=(pcm_full, active_source),
                                    daemon=True
                                ).start()
                            else:
                                accumulated_chunks = []

        except Exception as e:
            print("[MeetListener] Erreur dans la boucle audio Meet :", e)
        finally:
            if stream_loop:
                try:
                    stream_loop.stop_stream()
                    stream_loop.close()
                except Exception:
                    pass
            if stream_mic:
                try:
                    stream_mic.stop_stream()
                    stream_mic.close()
                except Exception:
                    pass
            if pa:
                try:
                    pa.terminate()
                except Exception:
                    pass
            self.is_running = False
            self.status_changed.emit(False)

    def _process_speech_chunk(self, pcm_bytes: bytes, source: str = "Audio"):
        """Transcrit le bloc vocal, normalise l'audio si nécessaire et détecte les questions."""
        try:
            if len(pcm_bytes) < 400:
                return

            # Normalisation audio douce pour optimiser la reconnaissance
            audio_data = np.frombuffer(pcm_bytes, dtype=np.int16)
            peak = int(np.max(np.abs(audio_data))) if len(audio_data) > 0 else 0
            if 50 < peak < 9000:
                gain = min(2.5, 14000.0 / float(peak))
                audio_data = np.clip(audio_data.astype(np.float32) * gain, -32767, 32767).astype(np.int16)
                pcm_bytes = audio_data.tobytes()

            # Cascade STT : Antigravity Natif (Connect-RPC) -> Google Speech Cloud -> Windows Local
            text = transcribe_audio(pcm_bytes)
            if not text:
                text = transcribe_audio_google(pcm_bytes)

            if not text or len(text.strip()) < 3:
                return

            text = text.strip()
            is_q = is_teacher_question(text)
            self.speech_transcribed.emit(text, is_q)

            if is_q:
                print(f"[MeetListener] 🎓 QUESTION PROFESSEUR DÉTECTÉE ({source}) : « {text} »")
                self.question_detected.emit(text)
            else:
                print(f"[MeetListener] 💬 Parole professeur ({source}) : « {text} »")

        except Exception as e:
            print("[MeetListener] Erreur traitement transcription bloc audio :", e)
