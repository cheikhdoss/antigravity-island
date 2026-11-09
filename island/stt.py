import os
import subprocess
import json

PS_STT_SCRIPT = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "AntigravityIsland",
    "stt_worker.ps1"
)

PS_STT_TEMPLATE = """
param(
    [Parameter(Mandatory=$true)]
    [string]$AudioPath
)

try {
    Add-Type -AssemblyName System.Speech
    $culture = [System.Globalization.CultureInfo]::GetCultureInfo("fr-FR")
    $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)
    $grammar = New-Object System.Speech.Recognition.DictationGrammar
    $engine.LoadGrammar($grammar)

    $engine.SetInputToWaveFile($AudioPath)
    $result = $engine.Recognize([System.TimeSpan]::FromSeconds(8))
    if ($result -and $result.Text) {
        Write-Output $result.Text
    } else {
        Write-Output ""
    }
} catch {
    Write-Output ""
}
"""

def ensure_stt_worker():
    if not os.path.exists(PS_STT_SCRIPT):
        os.makedirs(os.path.dirname(PS_STT_SCRIPT), exist_ok=True)
        with open(PS_STT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(PS_STT_TEMPLATE)

def transcribe_audio(audio_path: str) -> str:
    """Transcrit un fichier WAV en texte via le moteur de reconnaissance vocale natif Windows fr-FR."""
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
        return ""

    ensure_stt_worker()
    try:
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", PS_STT_SCRIPT,
            "-AudioPath", os.path.abspath(audio_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=10)
        return res.stdout.strip()
    except Exception as e:
        print("[STT] Erreur transcription audio:", e)
        return ""
