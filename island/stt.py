import os
import subprocess
import time
import http.client
import ssl
import json
import re
import struct
import base64
import wave
import threading
import psutil

try:
    import speech_recognition as sr
    _recognizer = sr.Recognizer()
    _recognizer.dynamic_energy_threshold = False
    _recognizer.energy_threshold = 300
    HAS_SR = True
except Exception:
    HAS_SR = False

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

_agy_stt_cached_port = None
_agy_stt_cached_csrf = None

def _get_language_server_connection():
    global _agy_stt_cached_port, _agy_stt_cached_csrf
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    if _agy_stt_cached_port and _agy_stt_cached_csrf:
        try:
            conn = http.client.HTTPSConnection('127.0.0.1', _agy_stt_cached_port, context=ctx, timeout=0.8)
            conn.request('GET', '/')
            r = conn.getresponse()
            if r.status == 200:
                return _agy_stt_cached_port, _agy_stt_cached_csrf, ctx
        except Exception:
            _agy_stt_cached_port = None
            _agy_stt_cached_csrf = None

    ports = []
    for p in psutil.process_iter(['name', 'pid']):
        try:
            if p.info['name'] and 'language_server' in p.info['name'].lower():
                proc = psutil.Process(p.info['pid'])
                for conn_info in proc.net_connections():
                    if conn_info.status == 'LISTEN' and conn_info.laddr.ip in ('127.0.0.1', '0.0.0.0'):
                        ports.append(conn_info.laddr.port)
        except Exception:
            pass

    for port in ports:
        try:
            conn = http.client.HTTPSConnection('127.0.0.1', port, context=ctx, timeout=0.8)
            conn.request('GET', '/')
            resp = conn.getresponse()
            if resp.status == 200:
                html = resp.read().decode('utf-8')
                m = re.search(r'"csrfToken":"([^"]+)"', html)
                if m:
                    _agy_stt_cached_port = port
                    _agy_stt_cached_csrf = m.group(1)
                    return _agy_stt_cached_port, _agy_stt_cached_csrf, ctx
        except Exception:
            pass

    return None, None, ctx

def transcribe_audio_antigravity(audio_path: str, timeout: float = 6.0) -> str:
    """
    Transcrit l'audio via le moteur STT officiel Antigravity (Google LanguageServer StreamAudioTranscription).
    Précision maximale avec ponctuation et accents, exactement comme dans l'IDE Antigravity.
    """
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 400:
        return ""

    port, csrf, ctx = _get_language_server_connection()
    if not port or not csrf:
        return ""

    try:
        # 1. Ouvrir le flux StreamAudioTranscription Connect-RPC
        payload = json.dumps({'mimeType': 'audio/pcm;rate=16000', 'continuous': False}).encode('utf-8')
        envelope = struct.pack('>BI', 0, len(payload)) + payload

        stream_conn = http.client.HTTPSConnection('127.0.0.1', port, context=ctx, timeout=timeout)
        stream_conn.request(
            'POST',
            '/exa.language_server_pb.LanguageServerService/StreamAudioTranscription',
            body=envelope,
            headers={
                'Content-Type': 'application/connect+json',
                'x-codeium-csrf-token': csrf
            }
        )
        stream_resp = stream_conn.getresponse()
        if stream_resp.status != 200:
            return ""

        hdr = stream_resp.read(5)
        if not hdr or len(hdr) < 5:
            return ""
        flag, mlen = struct.unpack('>BI', hdr)
        ready_msg = json.loads(stream_resp.read(mlen).decode('utf-8'))
        session_id = ready_msg.get('ready', {}).get('sessionId')
        if not session_id:
            return ""

        final_text = []
        done_evt = threading.Event()

        def reader():
            while True:
                try:
                    h = stream_resp.read(5)
                    if not h or len(h) < 5:
                        break
                    fl, l = struct.unpack('>BI', h)
                    body = json.loads(stream_resp.read(l).decode('utf-8'))
                    if 'transcription' in body:
                        tr = body['transcription']
                        txt = tr.get('text', '')
                        if txt:
                            final_text.append(txt)
                        if tr.get('isFinal', False):
                            done_evt.set()
                            break
                    elif 'complete' in body or fl == 2:
                        break
                except Exception:
                    break
            done_evt.set()

        threading.Thread(target=reader, daemon=True).start()

        with wave.open(audio_path, 'rb') as wf:
            audio_bytes = wf.readframes(wf.getnframes())

        send_conn = http.client.HTTPSConnection('127.0.0.1', port, context=ctx, timeout=3.0)
        chunk_size = 16000  # 500ms
        seq = 0
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i+chunk_size]
            chunk_payload = json.dumps({
                'sessionId': session_id,
                'data': base64.b64encode(chunk).decode('ascii'),
                'sequenceNumber': seq
            }).encode('utf-8')

            send_conn.request(
                'POST',
                '/exa.language_server_pb.LanguageServerService/SendAudioChunk',
                body=chunk_payload,
                headers={
                    'Content-Type': 'application/json',
                    'x-codeium-csrf-token': csrf
                }
            )
            send_conn.getresponse().read()
            seq += 1

        end_payload = json.dumps({
            'sessionId': session_id,
            'lastSequenceNumber': seq - 1
        }).encode('utf-8')

        send_conn.request(
            'POST',
            '/exa.language_server_pb.LanguageServerService/EndAudioSession',
            body=end_payload,
            headers={
                'Content-Type': 'application/json',
                'x-codeium-csrf-token': csrf
            }
        )
        send_conn.getresponse().read()
        send_conn.close()

        done_evt.wait(timeout=timeout)
        stream_conn.close()

        if final_text:
            text = final_text[-1].strip()
            print(f"[STT Antigravity Natif] Transcription réussie : '{text}'")
            return text

    except Exception as e:
        print(f"[STT Antigravity Natif] Erreur : {e}")

    return ""

def transcribe_audio_google(audio_path: str) -> str:
    """
    Transcrit l'audio via l'API Google Cloud Speech en français.
    """
    if not HAS_SR or not os.path.exists(audio_path) or os.path.getsize(audio_path) < 400:
        return ""

    try:
        with sr.AudioFile(audio_path) as source:
            audio = _recognizer.record(source)

        text = _recognizer.recognize_google(audio, language="fr-FR")
        if text and text.strip():
            print(f"[STT Google] Transcription réussie : '{text.strip()}'")
            return text.strip()
    except sr.UnknownValueError:
        print("[STT Google] Aucun mot reconnaissable.")
    except Exception as e:
        print(f"[STT Google] Réseau ou repli : {e}")

    return ""

def transcribe_audio_offline(audio_path: str) -> str:
    """
    Fallback hors-ligne utilisant le moteur local Windows System.Speech.
    """
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 400:
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
            timeout=10,
            creationflags=0x08000000
        )
        if res.stdout:
            out = res.stdout.strip()
            if out:
                print(f"[STT Windows Local] Transcription : '{out}'")
                return out
    except Exception as e:
        print("[STT Windows Local] Erreur :", e)

    return ""

def transcribe_audio(audio_path: str) -> str:
    """
    Pipeline de transcription hiérarchique :
    1. Moteur officiel Antigravity Natif (Google DeepMind LanguageServer)
    2. Fallback Google Speech
    3. Fallback Windows Local
    """
    t0 = time.time()

    # 1. Moteur officiel Antigravity natif
    result_agy = transcribe_audio_antigravity(audio_path)
    if result_agy:
        print(f"[STT] Transcrit en {time.time()-t0:.2f}s via Antigravity Natif : '{result_agy}'")
        return result_agy

    # 2. Fallback Google Cloud Speech
    result_google = transcribe_audio_google(audio_path)
    if result_google:
        print(f"[STT] Transcrit en {time.time()-t0:.2f}s via Google Speech : '{result_google}'")
        return result_google

    # 3. Fallback Local
    result_offline = transcribe_audio_offline(audio_path)
    if result_offline:
        print(f"[STT] Transcrit en {time.time()-t0:.2f}s via Fallback Local : '{result_offline}'")
        return result_offline

    return ""
