import os
import json
import subprocess
import time
from island.vision import capture_screen

appdata_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AntigravityIsland")
os.makedirs(appdata_dir, exist_ok=True)
OCR_WORKER_SCRIPT = os.path.join(appdata_dir, "ocr_engine.ps1")

PS_OCR_TEMPLATE = """
param(
    [Parameter(Mandatory=$true)]
    [string]$ImagePath,
    [string]$SearchQuery = ""
)

Add-Type -AssemblyName System.Runtime.WindowsRuntime

[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) {
    Write-Output "[]"
    exit
}

$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
} | Select-Object -First 1

function Await-AsyncOp($asyncOp, $targetType) {
    $method = $asTaskGeneric.MakeGenericMethod($targetType)
    $task = $method.Invoke($null, @($asyncOp))
    return $task.GetAwaiter().GetResult()
}

$resolvedPath = (Resolve-Path $ImagePath).Path
$fileOp = [Windows.Storage.StorageFile]::GetFileFromPathAsync($resolvedPath)
$file = Await-AsyncOp $fileOp ([Windows.Storage.StorageFile])

$streamOp = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
$stream = Await-AsyncOp $streamOp ([Windows.Storage.Streams.IRandomAccessStream])

$decoderOp = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
$decoder = Await-AsyncOp $decoderOp ([Windows.Graphics.Imaging.BitmapDecoder])

$bitmapOp = $decoder.GetSoftwareBitmapAsync()
$bitmap = Await-AsyncOp $bitmapOp ([Windows.Graphics.Imaging.SoftwareBitmap])

$ocrOp = $engine.RecognizeAsync($bitmap)
$ocrResult = Await-AsyncOp $ocrOp ([Windows.Media.Ocr.OcrResult])

$matches = @()
foreach ($line in $ocrResult.Lines) {
    if (-not $SearchQuery -or ($line.Text.ToLower().Contains($SearchQuery.ToLower()))) {
        $minX = 999999; $minY = 999999; $maxX = 0; $maxY = 0
        foreach ($w in $line.Words) {
            $r = $w.BoundingRect
            if ($r.X -lt $minX) { $minX = $r.X }
            if ($r.Y -lt $minY) { $minY = $r.Y }
            if (($r.X + $r.Width) -gt $maxX) { $maxX = $r.X + $r.Width }
            if (($r.Y + $r.Height) -gt $maxY) { $maxY = $r.Y + $r.Height }
        }
        $matches += [PSCustomObject]@{
            text = $line.Text
            x = [int]$minX
            y = [int]$minY
            width = [int]($maxX - $minX)
            height = [int]($maxY - $minY)
            center_x = [int]($minX + ($maxX - $minX) / 2)
            center_y = [int]($minY + ($maxY - $minY) / 2)
        }
    }
}

$matches | ConvertTo-Json -Compress
"""

def ensure_ocr_worker():
    if not os.path.exists(OCR_WORKER_SCRIPT):
        with open(OCR_WORKER_SCRIPT, "w", encoding="utf-8") as f:
            f.write(PS_OCR_TEMPLATE)

def find_screen_elements(query: str = "", image_path: str = None) -> list:
    """
    Analyse l'écran avec le moteur OCR natif Windows et retourne tous les éléments de texte
    correspondants avec leurs coordonnées pixel exactes (center_x, center_y, width, height).
    """
    ensure_ocr_worker()

    if not image_path or not os.path.exists(image_path):
        # Capture instantanée si aucun fichier fourni
        shot_res = capture_screen()
        if shot_res.get("status") == "success":
            image_path = shot_res["file_path"]
        else:
            return []

    # Vérification de sécurité : si la capture est vide/noire (< 30 KB), basculer sur la dernière capture valide
    if os.path.exists(image_path) and os.path.getsize(image_path) < 30000:
        import glob
        shot_dir = os.path.dirname(image_path)
        valid_shots = [
            f for f in glob.glob(os.path.join(shot_dir, "screen_*.png"))
            if os.path.getsize(f) > 50000 and not f.endswith("screen_latest.png")
        ]
        if valid_shots:
            valid_shots.sort(key=os.path.getmtime, reverse=True)
            image_path = valid_shots[0]

    try:
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", OCR_WORKER_SCRIPT,
            "-ImagePath", os.path.abspath(image_path)
        ]
        if query:
            cmd.extend(["-SearchQuery", query])

        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=6)
        out = res.stdout.strip()
        if not out:
            return []
        
        data = json.loads(out)
        if isinstance(data, dict):
            return [data]
        elif isinstance(data, list):
            return data
        return []
    except Exception as e:
        print("[OCR] Erreur détection éléments:", e)
        return []
