import os
import time
import threading
import numpy as np
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

try:
    import pyaudiowpatch as pyaudio
    HAS_PYAUDIO_WPATCH = True
except Exception:
    HAS_PYAUDIO_WPATCH = False

from island.stt import transcribe_audio_google, transcribe_audio

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
    "que signifie", "que veut dire", "qu'est-ce que cela signifie",
    "à quoi sert", "a quoi sert", "ça sert à quoi", "ca sert a quoi",
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
    if len(norm) < 5:
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
        "lesquels", "lesquelles", "qu'est-ce", "que", "quoi", "où", "ou"
    ]:
        return True

    return False

def resample_to_16k_mono(pcm_bytes: bytes, orig_rate: int, orig_channels: int) -> bytes:
    """Ré-échantillonne le flux audio 48kHz stéréo en 16kHz mono 16-bit pour le moteur STT."""
    try:
        audio = np.frombuffer(pcm_bytes, dtype=np.int16)
        if orig_channels == 2:
            audio = audio.reshape(-1, 2)
            audio = audio.mean(axis=1).astype(np.int16)
        elif orig_channels > 2:
            audio = audio.reshape(-1, orig_channels)
            audio = audio[:, 0].astype(np.int16)

        if orig_rate != 16000 and len(audio) > 0:
            num_target_samples = int(len(audio) * 16000 / orig_rate)
            if num_target_samples > 0:
                indices = np.linspace(0, len(audio) - 1, num_target_samples)
                audio = np.interp(indices, np.arange(len(audio)), audio).astype(np.int16)

        return audio.tobytes()
    except Exception as e:
        print("[MeetListener] Erreur ré-échantillonnage:", e)
        return b""

class MeetListener(QObject):
    """
    Écouteur en arrière-plan du flux haut-parleurs (WASAPI Loopback).
    Capture en continu la voix du professeur lors d'un Google Meet / Teams / Zoom,
    transcrit les paroles et déclenche automatiquement l'analyse contextuelle de l'écran
    dès qu'une question est posée.
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
        
        # Seuils acoustiques VAD (Voice Activity Detection)
        self.energy_threshold = 70.0    # RMS minimum pour considérer de la parole
        self.silence_timeout = 1.2      # Secondes de silence pour sceller une phrase
        self.max_phrase_duration = 10.0 # Durée maximale avant transcription forcée
        self.min_speech_duration = 0.7  # Durée minimale pour éviter les bruits parasites

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
            print("[MeetListener] pyaudiowpatch non disponible. Impossible d'activer le mode loopback.")
            return

        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loopback_loop, daemon=True)
        self._thread.start()
        self.status_changed.emit(True)
        print("[MeetListener] Mode Meet ACTIVÉ : écoute continue du flux haut-parleurs (WASAPI Loopback).")

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

    def _run_loopback_loop(self):
        """Boucle de capture audio WASAPI Loopback ultra-performante et résiliente."""
        pa = None
        stream = None
        try:
            pa = pyaudio.PyAudio()
            wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = pa.get_device_info_by_index(wasapi_info['defaultOutputDevice'])
            
            # Recherche du périphérique loopback correspondant aux haut-parleurs par défaut
            loopback_device = None
            if default_speakers.get('isLoopbackDevice', False):
                loopback_device = default_speakers
            else:
                for loopback in pa.get_loopback_device_info_generator():
                    if default_speakers['name'] in loopback['name']:
                        loopback_device = loopback
                        break

            if not loopback_device:
                # Fallback sur le premier périphérique loopback disponible
                for loopback in pa.get_loopback_device_info_generator():
                    loopback_device = loopback
                    break

            if not loopback_device:
                print("[MeetListener] Aucun périphérique WASAPI Loopback détecté.")
                self.is_running = False
                self.status_changed.emit(False)
                return

            rate = int(loopback_device['defaultSampleRate'])
            channels = int(loopback_device['maxInputChannels'])
            chunk_size = 1024

            print(f"[MeetListener] Connexion loopback établie : {loopback_device['name']} ({rate}Hz, {channels}ch)")

            stream = pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                frames_per_buffer=chunk_size,
                input=True,
                input_device_index=loopback_device['index']
            )

            accumulated_speech_chunks = []
            is_speaking = False
            last_speech_time = 0.0
            phrase_start_time = 0.0

            while not self._stop_event.is_set():
                try:
                    data = stream.read(chunk_size, exception_on_overflow=False)
                    if not data:
                        time.sleep(0.01)
                        continue

                    # Calcul de l'énergie RMS du bloc
                    samples = np.frombuffer(data, dtype=np.int16)
                    if len(samples) == 0:
                        continue
                    rms = float(np.sqrt(np.mean(samples.astype(np.float64)**2)))
                    self.rms_updated.emit(rms)

                    # Conversion immédiate du chunk vers 16kHz mono
                    resampled_chunk = resample_to_16k_mono(data, rate, channels)
                    now = time.time()

                    if rms >= self.energy_threshold:
                        if not is_speaking:
                            is_speaking = True
                            phrase_start_time = now
                            accumulated_speech_chunks = []
                        last_speech_time = now
                        accumulated_speech_chunks.append(resampled_chunk)
                    else:
                        if is_speaking:
                            # Ajout d'un court silence pour ne pas tronquer la fin
                            accumulated_speech_chunks.append(resampled_chunk)
                            # Si le silence dépasse le seuil ou si la phrase est trop longue
                            silence_dur = now - last_speech_time
                            phrase_dur = now - phrase_start_time
                            if silence_dur >= self.silence_timeout or phrase_dur >= self.max_phrase_duration:
                                is_speaking = False
                                if phrase_dur >= self.min_speech_duration and len(accumulated_speech_chunks) > 0:
                                    # Transcription de la phrase capturée
                                    pcm_full = b"".join(accumulated_speech_chunks)
                                    accumulated_speech_chunks = []
                                    # Traitement asynchrone pour ne jamais bloquer la capture continue
                                    threading.Thread(
                                        target=self._process_speech_chunk,
                                        args=(pcm_full,),
                                        daemon=True
                                    ).start()

                except Exception as loop_err:
                    time.sleep(0.02)

        except Exception as e:
            print("[MeetListener] Erreur boucle principale Loopback :", e)
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if pa:
                try:
                    pa.terminate()
                except Exception:
                    pass
            self.is_running = False
            self.status_changed.emit(False)

    def _process_speech_chunk(self, pcm_bytes: bytes):
        """Transcrit le bloc vocal et détecte si une question a été posée par le professeur."""
        try:
            # Essai Google Cloud Speech puis Antigravity Connect-RPC
            text = transcribe_audio_google(pcm_bytes)
            if not text:
                text = transcribe_audio(pcm_bytes)

            if not text or len(text.strip()) < 4:
                return

            text = text.strip()
            is_q = is_teacher_question(text)
            self.speech_transcribed.emit(text, is_q)

            if is_q:
                print(f"[MeetListener] 🎓 QUESTION DÉTECTÉE DU PROFESSEUR : « {text} »")
                self.question_detected.emit(text)
            else:
                print(f"[MeetListener] 💬 Parole professeur (explication / cours) : « {text} »")

        except Exception as e:
            print("[MeetListener] Erreur traitement transcription bloc audio :", e)
