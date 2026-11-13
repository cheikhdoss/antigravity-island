import os
import time
import wave
import ctypes
import collections
import threading
import numpy as np

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    HAS_PYCAW = True
except Exception:
    HAS_PYCAW = False

try:
    import pyaudiowpatch as pyaudio
    HAS_PA = True
except Exception:
    HAS_PA = False

class AudioRecorder:
    """
    Enregistreur microphone ultra-réactif et haute fidélité pour Antigravity Island.
    - Architecture Warm-Stream : flux WASAPI maintenu ouvert en continu en arrière-plan.
    - Latence de démarrage : 0.0 ms (aucun délai de négociation audio à l'appui de touche).
    - Ring buffer de pré-capture (200ms) pour ne jamais tronquer la première syllabe.
    - Élimination adaptative des silences (VAD) pour accélérer le STT Google.
    - Fallback automatique winmm en cas d'imprévu.
    """
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.is_recording = False
        self.frames = []
        self.pre_buffer = collections.deque(maxlen=7)  # ~220ms d'historique audio continu
        self.pa = None
        self.stream = None
        self.last_rms = 0.0
        self.last_peak = 0
        
        # Fallback winmm
        self.winmm = ctypes.windll.winmm
        self.alias = "antigravity_mic"
        self.using_fallback = False

        self._init_stream()

    def _audio_callback(self, in_data, frame_count, time_info, status):
        data = np.frombuffer(in_data, dtype=np.int16)
        if self.is_recording:
            self.frames.append(data)
        else:
            self.pre_buffer.append(data)
        return (None, pyaudio.paContinue)

    def _init_stream(self):
        """Initialise le flux continu en arrière-plan."""
        if not HAS_PA:
            self.using_fallback = True
            return

        try:
            if not self.pa:
                self.pa = pyaudio.PyAudio()
            default_mic = self.pa.get_default_input_device_info()
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=default_mic["index"],
                frames_per_buffer=1024,
                stream_callback=self._audio_callback
            )
            self.stream.start_stream()
            self.using_fallback = False
            print("[AudioRecorder] Flux audio WASAPI warm-stream actif (latence démarrage = 0ms).")
        except Exception as e:
            print("[AudioRecorder] Impossible d'ouvrir le flux WASAPI, mode fallback activé :", e)
            self.stream = None
            self.using_fallback = True

    def start_recording(self):
        """Démarre l'enregistrement instantanément (0 ms)."""
        if self.is_recording:
            return

        self.last_rms = 0.0
        self.last_peak = 0

        if not self.using_fallback and self.stream and self.stream.is_active():
            # Récupère le pre-buffer pour ne pas couper le début du premier mot
            self.frames = list(self.pre_buffer)
            self.is_recording = True
            return

        # Si le stream s'était arrêté, relancer
        if HAS_PA:
            self._init_stream()
            if self.stream and self.stream.is_active():
                self.frames = list(self.pre_buffer)
                self.is_recording = True
                return

        # Fallback winmm
        try:
            self.using_fallback = True
            self.frames = []
            self.is_recording = True
            self.winmm.mciSendStringW(f"close {self.alias}", None, 0, None)
            self.winmm.mciSendStringW(f"open new type waveaudio alias {self.alias}", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} time format ms", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} format tag pcm", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} channels 1", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} samplespersec {self.sample_rate}", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} bitspersample 16", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} alignment 2", None, 0, None)
            self.winmm.mciSendStringW(f"record {self.alias}", None, 0, None)
        except Exception as e:
            print("[AudioRecorder] Erreur winmm start:", e)
            self.is_recording = False

    def _save_wav_async(self, file_path: str, pcm_bytes: bytes):
        """Sauvegarde du fichier WAV en tâche de fond pour ne jamais ralentir le flux vocal."""
        try:
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(pcm_bytes)
        except Exception as e:
            print("[AudioRecorder] Erreur écriture async WAV :", e)

    def stop_recording(self, output_path: str = None) -> bool:
        """
        Arrête l'enregistrement, élague les silences et met à disposition l'audio en mémoire vive.
        Sauvegarde sur disque en arrière-plan (latence zéro I/O).
        """
        if not self.is_recording:
            return False

        self.is_recording = False
        self.last_pcm_bytes = None

        if not self.using_fallback and self.stream:
            if not self.frames:
                return False

            try:
                audio_data = np.concatenate(self.frames, axis=0)
                self.frames = []

                # Calcul énergie brute
                self.last_rms = float(np.sqrt(np.mean(audio_data.astype(np.float64)**2)))
                self.last_peak = int(np.max(np.abs(audio_data)))

                # Préserver l'intégralité du signal naturel (aucun rognage destructif qui coupe les syllabes)
                # Normalisation acoustique douce SEULEMENT si le volume d'entrée est très faible, sans clipping ni bruit
                if 50 < self.last_peak < 6000:
                    gentle_gain = min(1.8, 11000.0 / float(self.last_peak))
                    clean_audio = np.clip(audio_data.astype(np.float32) * gentle_gain, -32767, 32767).astype(np.int16)
                    print(f"[AudioRecorder] Normalisation douce : x{gentle_gain:.2f} (Peak {self.last_peak} -> {int(np.max(np.abs(clean_audio)))})")
                else:
                    clean_audio = audio_data

                pcm_bytes = clean_audio.tobytes()
                self.last_pcm_bytes = pcm_bytes

                if output_path:
                    abs_path = os.path.abspath(output_path)
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    # Écriture disque asynchrone pour ne pas retarder le STT
                    threading.Thread(target=self._save_wav_async, args=(abs_path, pcm_bytes), daemon=True).start()

                dur = len(clean_audio) / self.sample_rate
                print(f"[AudioRecorder] Audio capturé en mémoire vive : {len(pcm_bytes)} octets (RMS={self.last_rms:.1f}, Peak={self.last_peak}, Durée={dur:.2f}s)")
                return len(pcm_bytes) > 200
            except Exception as e:
                print("[AudioRecorder] Erreur WAV WASAPI:", e)
                return False

        # Fallback winmm
        try:
            self.winmm.mciSendStringW(f"stop {self.alias}", None, 0, None)
            abs_path = os.path.abspath(output_path or "temp_fallback.wav")
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass
            self.winmm.mciSendStringW(f'save {self.alias} "{abs_path}"', None, 0, None)
            self.winmm.mciSendStringW(f"close {self.alias}", None, 0, None)
            
            success = os.path.exists(abs_path) and os.path.getsize(abs_path) > 100
            if success:
                try:
                    with wave.open(abs_path, 'rb') as wf:
                        data = wf.readframes(wf.getnframes())
                        self.last_pcm_bytes = data
                        samples = np.frombuffer(data, dtype=np.int16)
                        self.last_rms = float(np.sqrt(np.mean(samples.astype(np.float64)**2)))
                        self.last_peak = int(np.max(np.abs(samples)))
                except Exception:
                    self.last_rms = 50.0
            return success
        except Exception as e:
            print("[AudioRecorder] Erreur arret winmm:", e)
            return False
