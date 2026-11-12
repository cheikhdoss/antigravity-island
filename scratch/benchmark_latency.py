import time
import os
import wave
import json
import threading
import numpy as np
from typing import Dict, Any

def run_benchmark(iterations: int = 5) -> Dict[str, Any]:
    sample_rate = 16000
    duration = 1.8  # Échantillon vocal typique de 1.8 seconde
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    signal = (np.sin(2 * np.pi * 220 * t) * 0.4 + np.sin(2 * np.pi * 440 * t) * 0.3 + np.sin(2 * np.pi * 880 * t) * 0.15)
    raw_audio = (signal * 12000).astype(np.int16)
    pcm_bytes = raw_audio.tobytes()

    appdata_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AntigravityIsland")
    os.makedirs(appdata_dir, exist_ok=True)
    test_wav_path = os.path.join(appdata_dir, "benchmark_temp.wav")

    old_results = []
    new_results = []

    print(f"=== BENCHMARK DE VITESSE : ANCIENNE vs NOUVELLE VERSION ({iterations} itérations) ===")
    print(f"Taille de l'échantillon audio : {len(pcm_bytes)} octets (durée {duration}s @ 16kHz)\n")

    for i in range(iterations):
        # -------------------------------------------------------------
        # 1. Pipeline ANCIENNE VERSION
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        
        # Étape A : Marge statique post-relâchement
        time.sleep(0.28)
        t_after_sleep = time.perf_counter()
        old_sleep_ms = (t_after_sleep - t0) * 1000

        # Étape B : Écriture bloquante sur SSD du fichier WAV
        t_w0 = time.perf_counter()
        with wave.open(test_wav_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        t_w1 = time.perf_counter()
        old_disk_write_ms = (t_w1 - t_w0) * 1000

        # Étape C : Relecture bloquante depuis le SSD pour le STT
        t_r0 = time.perf_counter()
        with wave.open(test_wav_path, 'rb') as wf:
            read_bytes = wf.readframes(wf.getnframes())
        t_r1 = time.perf_counter()
        old_disk_read_ms = (t_r1 - t_r0) * 1000

        # Étape D : Préparation du payload Connect-RPC
        import base64
        t_p0 = time.perf_counter()
        payload_old = base64.b64encode(read_bytes).decode('ascii')
        old_payload_ms = (time.perf_counter() - t_p0) * 1000

        old_total_ms = (time.perf_counter() - t0) * 1000
        old_results.append({
            "sleep_ms": old_sleep_ms,
            "disk_write_ms": old_disk_write_ms,
            "disk_read_ms": old_disk_read_ms,
            "payload_ms": old_payload_ms,
            "total_ms": old_total_ms
        })

        # -------------------------------------------------------------
        # 2. Pipeline NOUVELLE VERSION (Optimisée In-Memory)
        # -------------------------------------------------------------
        t_new0 = time.perf_counter()

        # Étape A : Marge réactive post-relâchement affinée
        time.sleep(0.09)
        t_new_sleep = time.perf_counter()
        new_sleep_ms = (t_new_sleep - t_new0) * 1000

        # Étape B : Extraction RAM directe & écriture asynchrone sans attente
        t_mem0 = time.perf_counter()
        in_memory_pcm = pcm_bytes  # Déjà en RAM
        def async_save():
            try:
                with wave.open(test_wav_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(in_memory_pcm)
            except Exception:
                pass
        threading.Thread(target=async_save, daemon=True).start()
        t_mem1 = time.perf_counter()
        new_mem_handoff_ms = (t_mem1 - t_mem0) * 1000

        # Étape C : Relecture disque = 0 ms (zéro accès SSD)
        new_disk_read_ms = 0.0

        # Étape D : Préparation du payload Connect-RPC direct
        t_new_p0 = time.perf_counter()
        payload_new = base64.b64encode(in_memory_pcm).decode('ascii')
        new_payload_ms = (time.perf_counter() - t_new_p0) * 1000

        new_total_ms = (time.perf_counter() - t_new0) * 1000
        new_results.append({
            "sleep_ms": new_sleep_ms,
            "mem_handoff_ms": new_mem_handoff_ms,
            "disk_read_ms": new_disk_read_ms,
            "payload_ms": new_payload_ms,
            "total_ms": new_total_ms
        })

    # Calcul des moyennes
    avg_old_total = np.mean([r["total_ms"] for r in old_results])
    avg_new_total = np.mean([r["total_ms"] for r in new_results])
    diff_ms = avg_old_total - avg_new_total
    speedup = avg_old_total / avg_new_total

    summary = {
        "avg_old_total_ms": round(avg_old_total, 2),
        "avg_new_total_ms": round(avg_new_total, 2),
        "diff_ms": round(diff_ms, 2),
        "speedup": round(speedup, 2),
        "details_old": {
            "sleep_ms": round(np.mean([r["sleep_ms"] for r in old_results]), 2),
            "disk_write_ms": round(np.mean([r["disk_write_ms"] for r in old_results]), 2),
            "disk_read_ms": round(np.mean([r["disk_read_ms"] for r in old_results]), 2),
            "payload_ms": round(np.mean([r["payload_ms"] for r in old_results]), 2)
        },
        "details_new": {
            "sleep_ms": round(np.mean([r["sleep_ms"] for r in new_results]), 2),
            "mem_handoff_ms": round(np.mean([r["mem_handoff_ms"] for r in new_results]), 2),
            "disk_read_ms": 0.0,
            "payload_ms": round(np.mean([r["payload_ms"] for r in new_results]), 2)
        }
    }

    print("\n--- RÉSULTATS DU BENCHMARK ---")
    print(f"Temps Moyen Ancienne Version : {summary['avg_old_total_ms']} ms")
    print(f"Temps Moyen Nouvelle Version : {summary['avg_new_total_ms']} ms")
    print(f"Gain net de temps : -{summary['diff_ms']} ms (Facteur d'accélération : x{summary['speedup']})")
    
    return summary

if __name__ == "__main__":
    res = run_benchmark(iterations=10)
    out_file = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"Rapport sauvegardé dans {out_file}")
