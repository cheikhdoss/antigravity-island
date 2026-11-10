import os
import time
import wave
import ctypes
import collections
import numpy as np

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    HAS_PYCAW = True
except Exception:
    HAS_PYCAW = False

try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    HAS_SD = False

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
        self.stream = None
        self.last_rms = 0.0
        self.last_peak = 0
        
        # Fallback winmm
        self.winmm = ctypes.windll.winmm
        self.alias = "antigravity_mic"
        self.using_fallback = False

        self._init_stream()

    def _ensure_mic_unmuted_quick(self):
        """Vérification rapide du volume micro sans bloquer le thread principal."""
        if not HAS_PYCAW:
            return
        try:
            mic = AudioUtilities.GetMicrophone()
            if mic:
                ep = mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                vol = ctypes.cast(ep, ctypes.POINTER(IAudioEndpointVolume))
                if vol.GetMute():
                    vol.SetMute(0, None)
                cur_lvl = vol.GetMasterVolumeLevelScalar()
                if cur_lvl < 0.85:
                    vol.SetMasterVolumeLevelScalar(1.0, None)
        except Exception:
            pass

    def _audio_callback(self, indata, frames_count, time_info, status):
        data = indata.copy()
        if self.is_recording:
            self.frames.append(data)
        else:
            self.pre_buffer.append(data)

    def _init_stream(self):
        """Initialise le flux continu en arrière-plan."""
        if not HAS_SD:
            self.using_fallback = True
            return

        try:
            self._ensure_mic_unmuted_quick()
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16',
                callback=self._audio_callback
            )
            self.stream.start()
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

        if not self.using_fallback and self.stream and self.stream.active:
            # Récupère le pre-buffer pour ne pas couper le début du premier mot
            self.frames = list(self.pre_buffer)
            self.is_recording = True
            return

        # Si le stream s'était arrêté, relancer
        if HAS_SD:
            self._init_stream()
            if self.stream and self.stream.active:
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

    def stop_recording(self, output_path: str) -> bool:
        """
        Arrête l'enregistrement, élague les silences et sauvegarde le fichier WAV.
        """
        if not self.is_recording:
            return False

        self.is_recording = False
        abs_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        if not self.using_fallback and self.stream:
            if not self.frames:
                return False

            try:
                audio_data = np.concatenate(self.frames, axis=0)
                self.frames = []

                # Calcul énergie brute
                self.last_rms = float(np.sqrt(np.mean(audio_data.astype(np.float64)**2)))
                self.last_peak = int(np.max(np.abs(audio_data)))

                # Élagage adaptatif des silences pour un envoi ultra-rapide au STT
                flat = np.abs(audio_data.flatten())
                thresh = max(180, int(self.last_peak * 0.08))
                non_silent = np.where(flat > thresh)[0]
                if len(non_silent) > 0:
                    start_pad = max(0, non_silent[0] - int(self.sample_rate * 0.15))
                    end_pad = min(len(audio_data), non_silent[-1] + int(self.sample_rate * 0.15))
                    clean_data = audio_data[start_pad:end_pad]
                else:
                    clean_data = audio_data

                # Amplification dynamique intelligente / AGC (Normalisation numérique haute fidélité)
                # Remonte le niveau du signal audio à ~24000 (environ 75% du maximum 32767)
                peak_clean = int(np.max(np.abs(clean_data))) if len(clean_data) > 0 else 0
                if peak_clean > 100:
                    target_peak = 24000.0
                    gain = min(15.0, target_peak / float(peak_clean))
                    amplified = np.clip(clean_data.astype(np.float32) * gain, -32767, 32767).astype(np.int16)
                    print(f"[AudioRecorder] Gain AGC appliqué : x{gain:.1f} (Peak {peak_clean} -> {int(np.max(np.abs(amplified)))})")
                else:
                    amplified = clean_data

                with wave.open(abs_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(amplified.tobytes())

                dur = len(clean_data) / self.sample_rate
                print(f"[AudioRecorder] Audio capturé : {abs_path} (RMS={self.last_rms:.1f}, Peak={self.last_peak}, Durée={dur:.2f}s)")
                return os.path.exists(abs_path) and os.path.getsize(abs_path) > 100
            except Exception as e:
                print("[AudioRecorder] Erreur WAV WASAPI:", e)
                return False

        # Fallback winmm
        try:
            self.winmm.mciSendStringW(f"stop {self.alias}", None, 0, None)
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
                        samples = np.frombuffer(data, dtype=np.int16)
                        self.last_rms = float(np.sqrt(np.mean(samples.astype(np.float64)**2)))
                        self.last_peak = int(np.max(np.abs(samples)))
                except Exception:
                    self.last_rms = 50.0
            return success
        except Exception as e:
            print("[AudioRecorder] Erreur arret winmm:", e)
            return False
