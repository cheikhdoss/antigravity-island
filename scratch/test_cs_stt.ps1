[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
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
        } catch (Exception ex) {
            return "ERROR:" + ex.Message;
        }
    }
}
'@

Add-Type -TypeDefinition $src -ReferencedAssemblies "System.Speech"

$audio = $args[0]
$res = [WinSTT]::Transcribe($audio, 5000)
Write-Output $res
