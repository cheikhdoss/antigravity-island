Add-Type -AssemblyName System.Speech
$culture = [System.Globalization.CultureInfo]::GetCultureInfo('fr-FR')
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$engine.LoadGrammar($grammar)

$engine.InitialSilenceTimeout = [System.TimeSpan]::FromSeconds(2)
$engine.EndSilenceTimeout = [System.TimeSpan]::FromSeconds(1)

$audio = 'C:\Users\pro\.gemini\antigravity\scratch\antigravity-island\scratch\test_rec_winmm.wav'
$engine.SetInputToWaveFile($audio)

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$result = $engine.Recognize([System.TimeSpan]::FromSeconds(3))
$sw.Stop()

Write-Host ('Duration: ' + $sw.ElapsedMilliseconds + ' ms')
if ($result) {
    Write-Host ('Result: ' + $result.Text)
} else {
    Write-Host 'Result: (null)'
}
