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
_agy_stt_lock = threading.Lock()
_ls_daemon_proc = None
_ls_daemon_port = 60899
_ls_daemon_csrf = "agy-stt-token-2026"

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
            r.read()
            conn.close()
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
                conn.close()
                m = re.search(r'"csrfToken":"([^"]+)"', html)
                if m:
                    _agy_stt_cached_port = port
                    _agy_stt_cached_csrf = m.group(1)
                    return _agy_stt_cached_port, _agy_stt_cached_csrf, ctx
            conn.close()
        except Exception:
            pass

    return None, None, ctx

def ensure_language_server_daemon():
    """Garantit qu'une instance du Language Server Antigravity est active pour le STT."""
    global _ls_daemon_proc, _agy_stt_cached_port, _agy_stt_cached_csrf
    port, csrf, ctx = _get_language_server_connection()
    if port and csrf:
        return port, csrf, ctx

    ls_bin = r"C:\Users\pro\AppData\Local\Programs\antigravity\resources\bin\language_server.exe"
    if not os.path.exists(ls_bin):
        return None, None, ctx

    if _ls_daemon_proc is None or _ls_daemon_proc.poll() is not None:
        cmd = [
            ls_bin,
            '--standalone',
            '--override_ide_name', 'antigravity',
            '--subclient_type', 'hub',
            '--override_ide_version', '1.5.3',
            '--override_user_agent_name', 'antigravity',
            '--https_server_port', str(_ls_daemon_port),
            '--csrf_token', _ls_daemon_csrf,
            '--app_data_dir', 'antigravity',
            '--api_server_url', 'https://generativelanguage.googleapis.com',
            '--cloud_code_endpoint', 'https://daily-cloudcode-pa.googleapis.com',
            '--enable_sidecars',
        ]
        try:
            _ls_daemon_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000
            )
            time.sleep(1.2)
            _agy_stt_cached_port = _ls_daemon_port
            _agy_stt_cached_csrf = _ls_daemon_csrf
            return _ls_daemon_port, _ls_daemon_csrf, ctx
        except Exception as e:
            print("[STT Daemon] Erreur lancement language_server standalone :", e)

    return None, None, ctx

def get_current_stt_provider() -> str:
    """Lit le fournisseur STT configuré dans settings.json ('antigravity', 'google', 'offline')."""
    try:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        settings_path = os.path.join(appdata, "AntigravityIsland", "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                return data.get("stt_provider", "antigravity")
    except Exception:
        pass
    return "antigravity"

def transcribe_audio_antigravity(audio_input, timeout: float = 3.5) -> str:
    """
    Transcrit l'audio via le moteur STT officiel Antigravity (Google LanguageServer StreamAudioTranscription).
    Précision maximale avec ponctuation et accents, supporte le flux audio 100% in-memory (bytes) ou chemin WAV.
    """
    if isinstance(audio_input, bytes):
        audio_bytes = audio_input
        if len(audio_bytes) < 400:
            return ""
    else:
        if not os.path.exists(audio_input) or os.path.getsize(audio_input) < 400:
            return ""
        try:
            with wave.open(audio_input, 'rb') as wf:
                audio_bytes = wf.readframes(wf.getnframes())
        except Exception:
            return ""

    with _agy_stt_lock:
        port, csrf, ctx = ensure_language_server_daemon()
        if not port or not csrf:
            return ""

        stream_conn = None
        send_conn = None
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

            send_conn = http.client.HTTPSConnection('127.0.0.1', port, context=ctx, timeout=2.5)
            # Envoi direct du buffer en mémoire (zéro attente I/O disque)
            chunk_payload = json.dumps({
                'sessionId': session_id,
                'data': base64.b64encode(audio_bytes).decode('ascii'),
                'sequenceNumber': 0
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

            end_payload = json.dumps({
                'sessionId': session_id,
                'lastSequenceNumber': 0
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

            if final_text:
                text = final_text[-1].strip()
                print(f"[STT Antigravity Natif] Transcription réussie : '{text}'")
                return text

        except Exception as e:
            print(f"[STT Antigravity Natif] Erreur : {e}")
        finally:
            try:
                if send_conn:
                    send_conn.close()
            except Exception:
                pass
            try:
                if stream_conn:
                    stream_conn.close()
            except Exception:
                pass

        return ""

def transcribe_audio_google(audio_input) -> str:
    """
    Transcrit l'audio via l'API Google Cloud Speech en français avec timeout strict.
    Supporte buffer mémoire PCM (bytes) ou chemin WAV.
    """
    if not HAS_SR:
        return ""

    import socket
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(3.0)
        if isinstance(audio_input, bytes):
            if len(audio_input) < 400:
                return ""
            audio = sr.AudioData(audio_input, 16000, 2)
        else:
            if not os.path.exists(audio_input) or os.path.getsize(audio_input) < 400:
                return ""
            with sr.AudioFile(audio_input) as source:
                audio = _recognizer.record(source)

        text = _recognizer.recognize_google(audio, language="fr-FR")
        if text and text.strip():
            print(f"[STT Google] Transcription réussie : '{text.strip()}'")
            return text.strip()
    except sr.UnknownValueError:
        print("[STT Google] Aucun mot reconnaissable.")
    except Exception as e:
        print(f"[STT Google] Réseau ou repli : {e}")
    finally:
        socket.setdefaulttimeout(old_timeout)

    return ""

def transcribe_audio_offline(audio_input) -> str:
    """
    Fallback hors-ligne utilisant le moteur local Windows System.Speech.
    """
    if isinstance(audio_input, bytes):
        appdata_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AntigravityIsland")
        tmp_wav = os.path.join(appdata_dir, "temp_offline_stt.wav")
        try:
            with wave.open(tmp_wav, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_input)
            audio_path = tmp_wav
        except Exception:
            return ""
    else:
        audio_path = audio_input

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
            timeout=8,
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

def transcribe_audio(audio_input) -> str:
    """
    Pipeline de transcription audio avec priorité absolue au moteur configuré.
    Par défaut : Moteur officiel Antigravity Natif (Google DeepMind LanguageServer Connect-RPC).
    Supporte les buffers bytes in-memory (latence zéro) ou les fichiers WAV.
    """
    t0 = time.time()
    provider = get_current_stt_provider()

    if provider == "antigravity":
        result = transcribe_audio_antigravity(audio_input)
        if result:
            print(f"[STT] Transcrit en {time.time()-t0:.2f}s via Antigravity Natif (DeepMind) : '{result}'")
            return result
        # Fallback de secours si le daemon local ne répond pas
        fallback_res = transcribe_audio_google(audio_input)
        if fallback_res:
            print(f"[STT] Transcrit en {time.time()-t0:.2f}s via Google Speech (Fallback) : '{fallback_res}'")
            return fallback_res
    elif provider == "google":
        result = transcribe_audio_google(audio_input)
        if result:
            print(f"[STT] Transcrit en {time.time()-t0:.2f}s via Google Speech : '{result}'")
            return result
    else:  # offline
        result = transcribe_audio_offline(audio_input)
        if result:
            print(f"[STT] Transcrit en {time.time()-t0:.2f}s via Fallback Local : '{result}'")
            return result

    # Dernier recours local si aucun service réseau n'a fonctionné
    result_off = transcribe_audio_offline(audio_input)
    if result_off:
        return result_off
    return ""
