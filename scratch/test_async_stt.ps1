Add-Type -AssemblyName System.Speech

$culture = [System.Globalization.CultureInfo]::GetCultureInfo("fr-FR")
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$engine.LoadGrammar($grammar)

$doneEvent = New-Object System.Threading.ManualResetEvent($false)
[string]$script:text = ""

$engine.add_RecognizeCompleted({
    param($sender, $args)
    if ($args.Result -and $args.Result.Text) {
        $script:text = $args.Result.Text
    }
    $doneEvent.Set() | Out-Null
})

$audio = $args[0]
if (-not (Test-Path $audio)) {
    Write-Output ""
    exit 0
}

$engine.SetInputToWaveFile($audio)
$engine.RecognizeAsync([System.Speech.Recognition.RecognizeMode]::Single)

# Attendre max 4 secondes
$done = $doneEvent.WaitOne(4000)
$engine.RecognizeAsyncCancel()
$engine.Dispose()

Write-Output $script:text
