import os
import subprocess
import time
import re

AGY_PATH = r"C:\Users\pro\AppData\Local\agy\bin\agy.EXE"

def query_agy_llm(user_query: str, timeout: int = 10) -> str:
    """Interroge le LLM Antigravity via agy CLI pour obtenir une réponse intelligente."""
    if not os.path.exists(AGY_PATH):
        return ""

    system_instruction = (
        "Consigne: Tu es Antigravity Island, le compagnon desktop intelligent de l'utilisateur. "
        "Réponds en français de manière concise, naturelle et fluide (1 à 2 phrases maximum, adaptées à la voix). "
        "Pas d'émojis, pas de code ni de markdown lourd.\n"
        f"Question de l'utilisateur: {user_query}\n"
        "Ta réponse:"
    )

    cmd = [
        AGY_PATH,
        "--print", system_instruction,
        "--disable-slash-commands",
        "--effort", "low",
        "--output-format", "text"
    ]

    try:
        t0 = time.time()
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        if res.returncode == 0 and res.stdout.strip():
            raw = res.stdout.strip()
            # Nettoyer les éventuels préfixes "Ta réponse :" ou guillemets superflus
            clean = re.sub(r'^(Antigravity\s*:|Réponse\s*:|Ta réponse\s*:)\s*', '', raw, flags=re.IGNORECASE)
            print(f"[Brain AGY] Réponse générée en {time.time() - t0:.2f}s : '{clean}'")
            return clean.strip()
    except subprocess.TimeoutExpired:
        print(f"[Brain AGY] Timeout ({timeout}s)")
    except Exception as e:
        print(f"[Brain AGY] Erreur : {e}")

    return ""

if __name__ == "__main__":
    q = "Quelle est la capitale du Sénégal et pourquoi est-elle connue ?"
    print("Testing query:", q)
    ans = query_agy_llm(q, timeout=12)
    print("Final answer:", ans)
