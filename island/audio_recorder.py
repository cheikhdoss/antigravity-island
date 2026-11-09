import ctypes
import os
import time

class AudioRecorder:
    """
    Enregistreur de microphone Windows natif sans aucune dépendance tierce (via winmm.dll).
    Enregistre l'audio du microphone par défaut au format WAV standard.
    """
    def __init__(self):
        self.winmm = ctypes.windll.winmm
        self.is_recording = False
        self.alias = "antigravity_mic"

    def start_recording(self):
        """Démarre l'enregistrement audio depuis le microphone."""
        if self.is_recording:
            return

        try:
            # S'assurer que l'alias précédent est fermé
            self.winmm.mciSendStringW(f"close {self.alias}", None, 0, None)
            
            # Ouvrir un nouveau flux waveaudio
            self.winmm.mciSendStringW(f"open new type waveaudio alias {self.alias}", None, 0, None)
            # Configurer le format audio (16-bit, 16000Hz mono PCM pour reconnaissance vocale optimale)
            self.winmm.mciSendStringW(f"set {self.alias} time format ms", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} format tag pcm", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} channels 1", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} samplespersec 16000", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} bitspersample 16", None, 0, None)
            self.winmm.mciSendStringW(f"set {self.alias} alignment 2", None, 0, None)
            
            # Lancer l'enregistrement
            res_rec = self.winmm.mciSendStringW(f"record {self.alias}", None, 0, None)
            self.is_recording = True
            print("[AudioRecorder] Enregistrement microphone demarre.")
        except Exception as e:
            print("[AudioRecorder] Erreur demarrage enregistrement:", e)
            self.is_recording = False

    def stop_recording(self, output_path: str) -> bool:
        """Arrête l'enregistrement et sauvegarde dans un fichier .wav."""
        if not self.is_recording:
            return False

        try:
            self.winmm.mciSendStringW(f"stop {self.alias}", None, 0, None)
            abs_path = os.path.abspath(output_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass
            
            res_save = self.winmm.mciSendStringW(f'save {self.alias} "{abs_path}"', None, 0, None)
            self.winmm.mciSendStringW(f"close {self.alias}", None, 0, None)
            self.is_recording = False
            
            success = os.path.exists(abs_path) and os.path.getsize(abs_path) > 100
            if success:
                print(f"[AudioRecorder] Audio sauvegarde ({os.path.getsize(abs_path)} octets) : {abs_path}")
            return success
        except Exception as e:
            print("[AudioRecorder] Erreur arret enregistrement:", e)
            try:
                self.winmm.mciSendStringW(f"close {self.alias}", None, 0, None)
            except Exception:
                pass
            self.is_recording = False
            return False
