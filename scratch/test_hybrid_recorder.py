import os
import time
import wave
import numpy as np

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    import ctypes
    HAS_PYCAW = True
except Exception:
    HAS_PYCAW = False

try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    HAS_SD = False

class SmartAudioRecorder:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.is_recording = False
        self.frames = []
        self.stream = None
        self._ensure_mic_unmuted()

    def _ensure_mic_unmuted(self):
        if not HAS_PYCAW:
            return
        try:
            mic = AudioUtilities.GetMicrophone()
            if mic:
                ep = mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                vol = ctypes.cast(ep, ctypes.POINTER(IAudioEndpointVolume))
                if vol.GetMute():
                    vol.SetMute(0, None)
                    print("[SmartAudioRecorder] Microphone reactive (demute)")
                cur_lvl = vol.GetMasterVolumeLevelScalar()
                if cur_lvl < 0.80:
                    vol.SetMasterVolumeLevelScalar(1.0, None)
                    print(f"[SmartAudioRecorder] Volume micro calibre a 100% (etait a {int(cur_lvl*100)}%)")
        except Exception as e:
            print("[SmartAudioRecorder] Verification CoreAudio:", e)

    def _audio_callback(self, indata, frames_count, time_info, status):
        if self.is_recording:
            self.frames.append(indata.copy())

    def start_recording(self):
        if self.is_recording:
            return
        self._ensure_mic_unmuted()
        self.frames = []
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
                print("[SmartAudioRecorder] Enregistrement WASAPI/sounddevice demarre.")
                return
            except Exception as e:
                print("[SmartAudioRecorder] Echec ouverture stream sounddevice, fallback:", e)
                self.stream = None

    def stop_recording(self, output_path: str):
        if not self.is_recording:
            return False, 0.0, 0

        self.is_recording = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        if not self.frames:
            print("[SmartAudioRecorder] Aucun frame capture.")
            return False, 0.0, 0

        audio_data = np.concatenate(self.frames, axis=0)
        rms = float(np.sqrt(np.mean(audio_data.astype(np.float64)**2)))
        peak = int(np.max(np.abs(audio_data)))
        
        abs_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
        with wave.open(abs_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        print(f"[SmartAudioRecorder] Fichier sauvegarde: {abs_path} (RMS={rms:.2f}, Peak={peak}, duree={len(audio_data)/self.sample_rate:.1f}s)")
        return True, rms, peak

if __name__ == "__main__":
    rec = SmartAudioRecorder()
    rec.start_recording()
    time.sleep(2)
    ok, rms, peak = rec.stop_recording(r"C:\Users\pro\.gemini\antigravity\scratch\antigravity-island\scratch\test_smart_rec.wav")
    print(f"Result: ok={ok}, rms={rms:.2f}, peak={peak}")
