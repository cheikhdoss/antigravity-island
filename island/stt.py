import os
import subprocess

PS_STT_SCRIPT = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "AntigravityIsland",
    "stt_worker.ps1"
)

PS_STT_TEMPLATE = r"""[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$src = @'
using System;
using System.IO;
using System.Speech.Recognition;
using System.Threading;

public class WinSTT {
    public static string Transcribe(string wavePath, int timeoutMs) {
        if (!File.Exists(wavePath)) return "";
        try {
            var culture = new System.Globalization.CultureInfo("fr-FR");
            using (var engine = new SpeechRecognitionEngine(culture)) {
                engine.LoadGrammar(new DictationGrammar());
                engine.SetInputToWaveFile(wavePath);
                
                string result = "";
                var done = new ManualResetEvent(false);
                
                engine.RecognizeCompleted += (s, e) => {
                    if (e.Result != null && !string.IsNullOrEmpty(e.Result.Text)) {
                        result = e.Result.Text;
                    }
                    done.Set();
                };
                
                engine.RecognizeAsync(RecognizeMode.Single);
                done.WaitOne(timeoutMs);
                engine.RecognizeAsyncCancel();
                return result;
            }
        } catch {
            return "";
        }
    }
}
'@

try {
    Add-Type -TypeDefinition $src -ReferencedAssemblies "System.Speech"
} catch {}

$audio = $args[0]
if (-not $audio -or -not (Test-Path $audio)) {
    [Console]::Out.WriteLine("")
    exit 0
}

$res = [WinSTT]::Transcribe($audio, 6000)
[Console]::Out.WriteLine($res)
"""

def ensure_stt_worker():
    os.makedirs(os.path.dirname(PS_STT_SCRIPT), exist_ok=True)
    with open(PS_STT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(PS_STT_TEMPLATE)

def transcribe_audio(audio_path: str) -> str:
    """
    Transcrit un fichier WAV en texte via le moteur de reconnaissance vocale natif Windows fr-FR.
    Asynchrone avec timeout strict pour ne jamais bloquer l'encoche ni le CPU.
    """
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 500:
        return ""

    ensure_stt_worker()
    try:
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", PS_STT_SCRIPT,
            os.path.abspath(audio_path)
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            creationflags=0x08000000  # CREATE_NO_WINDOW : empêche toute fenêtre de terminal
        )
        if res.stdout:
            return res.stdout.strip()
        return ""
    except Exception as e:
        print("[STT] Erreur transcription audio:", e)
        return ""
