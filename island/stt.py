import os
import subprocess

PS_STT_SCRIPT = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "AntigravityIsland",
    "stt_worker.ps1"
)

PS_STT_TEMPLATE = r"""param(
    [Parameter(Mandatory=$true)]
    [string]$AudioPath
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

if (-not (Test-Path $AudioPath)) {
    [Console]::Out.WriteLine("")
    exit 0
}

try {
    Add-Type -AssemblyName System.Speech
    $culture = [System.Globalization.CultureInfo]::GetCultureInfo("fr-FR")
    $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)
    $grammar = New-Object System.Speech.Recognition.DictationGrammar
    $engine.LoadGrammar($grammar)

    $engine.SetInputToWaveFile($AudioPath)
    $result = $engine.Recognize([System.TimeSpan]::FromSeconds(15))
    if ($result -and $result.Text) {
        [Console]::Out.WriteLine($result.Text)
    } else {
        [Console]::Out.WriteLine("")
    }
} catch {
    [Console]::Out.WriteLine("")
} finally {
    if ($engine) {
        $engine.Dispose()
    }
}
"""

def ensure_stt_worker():
    os.makedirs(os.path.dirname(PS_STT_SCRIPT), exist_ok=True)
    with open(PS_STT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(PS_STT_TEMPLATE)

def transcribe_audio(audio_path: str) -> str:
    """
    Transcrit un fichier WAV en texte via le moteur natif Windows System.Speech fr-FR.
    Sans compilation C#, ultra-rapide (GAC natif) et encodé proprement en UTF-8.
    """
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 500:
        return ""

    ensure_stt_worker()
    try:
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", PS_STT_SCRIPT,
            "-AudioPath", os.path.abspath(audio_path)
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=16,
            creationflags=0x08000000  # CREATE_NO_WINDOW : empêche toute fenêtre de console
        )
        if res.stdout:
            return res.stdout.strip()
        return ""
    except Exception as e:
        print("[STT] Erreur transcription audio:", e)
        return ""
