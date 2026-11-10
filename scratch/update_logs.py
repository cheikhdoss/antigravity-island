import os

entry = """
### 🎙️ Résolution Intégrale de la Détection Microphone & Reconnaissance Vocale (STT)
- **Constats & Diagnostics Réalisés** :
  1. *Autorisations Windows* : L'icône de notification Windows (icône blanche de micro actif dans la barre des tâches) a confirmé que Windows autorise bien l'application à accéder au microphone.
  2. *Niveau d'entrée Windows trop faible* : Le volume du microphone système était bridé à seulement 27% dans CoreAudio.
  3. *Bug critique d'encodage STT* : Dans `island/stt.py`, PowerShell retournait les accents français en CP1252/OEM, ce qui déclenchait une `UnicodeDecodeError` fatale lors du décodage UTF-8 en Python. La chaîne décodée était alors nulle et renvoyait systématiquement `""` (silence apparent).
  4. *Blocage synchrone du moteur System.Speech* : En l'absence de parole ou sur un audio court, `SpeechRecognitionEngine.Recognize(TimeSpan)` bloquait indéfiniment jusqu'au timeout subprocess.
  5. *Bug de machine d'état Push-to-Talk* : En mode hybride/bascule, appuyer une seconde fois pour arrêter l'écoute appelait à tort `start_recording()`, ce qui écrasait et réinitialisait l'audio enregistré avec 0.1s de blanc.
- **Correctifs Appliqués & Architecture** :
  1. *Module `island/audio_recorder.py`* : Implémentation d'un enregistreur WASAPI haute fidélité (`sounddevice` + `numpy`), avec détection CoreAudio (`pycaw`) pour rétablir automatiquement le microphone s'il est muet et forcer le volume d'entrée à 100%. Calcul d'énergie RMS et crête (Peak) en temps réel.
  2. *Module `island/stt.py`* : Script C# compilé asynchrone (`WinSTT.Transcribe`) avec gestion d'événements `RecognizeCompleted`, timeout strict et sortie forcée UTF-8. Reconnaissance vocale française instantanée (3-4s sur parole, <1s sur silence).
  3. *Machine d'état `island/hotkey.py`* : Correction du cycle de vie Push-to-Talk. L'enregistrement n'est plus réinitialisé lors de l'arrêt, et un message explicite s'affiche si le microphone matériel est coupé (`RMS < 3.0`).
  4. *Packaging & Déploiement* : Mise à jour du fichier `.spec`, recompilation PyInstaller et copie vers `C:\\Users\\pro\\Desktop\\AntigravityIsland`. Exécutable testé et opérationnel (PID actif, communication WebSocket validée, message MCP live projeté sur l'encoche).
"""

session_log = r"C:\Users\pro\second-brain\00-SESSION-LOG.md"
if os.path.exists(session_log):
    with open(session_log, "a", encoding="utf-8") as f:
        f.write(entry)
    print("Updated 00-SESSION-LOG.md")

daily_dir = r"C:\Users\pro\second-brain\005-DAILY"
os.makedirs(daily_dir, exist_ok=True)
daily_path = os.path.join(daily_dir, "2026-11-10.md")
with open(daily_path, "a", encoding="utf-8") as f:
    f.write(entry)
print("Updated daily note 2026-11-10.md")
