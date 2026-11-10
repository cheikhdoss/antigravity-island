import os
import time
import wave
import ctypes
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
    Enregistreur de microphone haute fidélité pour Antigravity Island.
    - Utilise sounddevice (WASAPI natif) comme moteur audio principal.
    - Calibre automatiquement le volume du microphone Windows à 100% et s'assure qu'il n'est pas muet via CoreAudio.
    - Analyse l'énergie (RMS et Peak) pour détecter si l'utilisateur a réellement parlé ou si le micro est silencieux.
    - Dispose d'un fallback automatique vers winmm.dll (MCI) en cas d'indisponibilité.
    """
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.is_recording = False
        self.frames = []
        self.stream = None
        self.last_rms = 0.0
        self.last_peak = 0
        
        # Fallback winmm
        self.winmm = ctypes.windll.winmm
        self.alias = "antigravity_mic"
        self.using_fallback = False

        self._ensure_mic_unmuted()

    def _ensure_mic_unmuted(self):
        """Vérifie l'état matériel/système du microphone via Windows CoreAudio et booste le volume à 100%."""
        if not HAS_PYCAW:
            return
        try:
            mic = AudioUtilities.GetMicrophone()
            if mic:
                ep = mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                vol = ctypes.cast(ep, ctypes.POINTER(IAudioEndpointVolume))
                if vol.GetMute():
                    vol.SetMute(0, None)
                    print("[AudioRecorder] Micro reactive (demute automatique)")
                
                cur_lvl = vol.GetMasterVolumeLevelScalar()
                if cur_lvl < 0.85:
                    vol.SetMasterVolumeLevelScalar(1.0, None)
                    print(f"[AudioRecorder] Volume micro calibre a 100% (etait a {int(cur_lvl*100)}%)")
        except Exception as e:
            print("[AudioRecorder] Verification CoreAudio:", e)

    def _audio_callback(self, indata, frames_count, time_info, status):
        if self.is_recording:
            self.frames.append(indata.copy())

    def start_recording(self):
        """Démarre l'enregistrement audio depuis le microphone."""
        if self.is_recording:
            return

        self._ensure_mic_unmuted()
        self.frames = []
        self.last_rms = 0.0
        self.last_peak = 0
        self.using_fallback = False
        self.is_recording = True

        if HAS_SD:
            try:
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='int16',
                    callback=self._audio_callback
                )
                self.stream.start()
                print("[AudioRecorder] Enregistrement WASAPI demarre.")
                return
            except Exception as e:
                print("[AudioRecorder] Echec stream WASAPI, bascule sur winmm:", e)
                self.stream = None

        # Fallback winmm (MCI)
        try:
            self.using_fallback = True
            self.winmm.mciSendStringW(f"close {self.alias}", None, 0, None)
            self.winmm.mciSendStringW(f"open new type waveaudio alias {self.alias}", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} time format ms", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} format tag pcm", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} channels 1", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} samplespersec {self.sample_rate}", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} bitspersample 16", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} alignment 2", None, 0, None)
            self.winmm.mciSendStringW(f"record {self.alias}", None, 0, None)
            print("[AudioRecorder] Enregistrement winmm (fallback) demarre.")
        except Exception as e:
            print("[AudioRecorder] Erreur winmm start:", e)
            self.is_recording = False

    def stop_recording(self, output_path: str) -> bool:
        """
        Arrête l'enregistrement, sauvegarde dans un fichier .wav et analyse l'énergie audio.
        Retourne True si un fichier audio valide a été sauvegardé.
        """
        if not self.is_recording:
            return False

        self.is_recording = False
        abs_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        if not self.using_fallback and self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

            if not self.frames:
                print("[AudioRecorder] Aucun frame capture via WASAPI.")
                return False

            try:
                audio_data = np.concatenate(self.frames, axis=0)
                self.last_rms = float(np.sqrt(np.mean(audio_data.astype(np.float64)**2)))
                self.last_peak = int(np.max(np.abs(audio_data)))

                with wave.open(abs_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(audio_data.tobytes())

                print(f"[AudioRecorder] Audio sauvegarde: {abs_path} (RMS={self.last_rms:.2f}, Peak={self.last_peak}, duree={len(audio_data)/self.sample_rate:.1f}s)")
                return os.path.exists(abs_path) and os.path.getsize(abs_path) > 100
            except Exception as e:
                print("[AudioRecorder] Erreur ecriture WAV WASAPI:", e)
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
                print(f"[AudioRecorder] Audio sauvegarde winmm: {abs_path} (RMS={self.last_rms:.2f})")
            return success
        except Exception as e:
            print("[AudioRecorder] Erreur arret winmm:", e)
            try:
                self.winmm.mciSendStringW(f"close {self.alias}", None, 0, None)
            except Exception:
                pass
            return False
