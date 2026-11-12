# Test complet d'intégration Harness² + RAG + WindowManager pour Antigravity Island
import sys
import os
import time

# Assurer que le dossier racine est dans sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

print(f"=== TEST INTEGRATION COMPLETE HARNESS² & RAG DANS ISLAND ===")
print(f"Base Directory: {BASE_DIR}")

# 1. Test import Google Research harness2 officiel
print("\n[1/4] Test import Google Research harness2...")
t0 = time.time()
try:
    import harness2
    from harness2.core import library as g_lib
    from harness2.core import context as g_ctx
    from harness2.core import recursion as g_rec
    print(f"  [OK] harness2 officiel importé avec succès en {time.time() - t0:.4f}s")
    print(f"  Version: {harness2.__version__ if hasattr(harness2, '__version__') else '0.1.0'}")
except Exception as e:
    print(f"  [FAIL] Erreur import harness2 : {e}")
    sys.exit(1)

# 2. Test RAG Indexer & Client
print("\n[2/4] Test RAG Indexer & Client...")
t0 = time.time()
try:
    from island.rag.client import RAGClient
    rag = RAGClient.get_instance()
    # Recherche d'un mot clé courant
    results = rag.search_files("python", limit=5)
    lookup_time = time.time() - t0
    print(f"  [OK] RAG indexé et interrogé en {lookup_time:.4f}s")
    print(f"  Fichiers trouvés ({len(results)}) :")
    for r in results[:3]:
        print(f"    - {r['name']} ({r['path']})")
except Exception as e:
    print(f"  [FAIL] Erreur RAG : {e}")
    sys.exit(1)

# 3. Test Harness Engine & Loop Propose-Probe-Compose
print("\n[3/4] Test HarnessEngine (Propose-Probe-Compose & Persistance)...")
t0 = time.time()
try:
    from island.harness.engine import HarnessEngine
    engine = HarnessEngine.get_instance()
    
    # Enregistrement d'une expérience test
    engine.library.record_experience(
        cue="ouvrir terminal powershell",
        lesson="Lancer powershell.exe en mode détaché sans console bloquante",
        evidence="Exécuté et vérifié en 0.05s",
        domain="system",
        task_id="test_powershell_launch"
    )
    
    # Vérification de rappel contextuel
    lessons = engine.get_context_lessons("powershell")
    print(f"  [OK] Leçons rappelées en mémoire :\n{lessons.strip()}")
    
    # Test probe sur fichier existant
    if results:
        sample_name = results[0]["name"]
        res = engine.execute_recursive(f"ouvre le fichier {sample_name}")
        print(f"  [OK] Résultat exécution récursive : {res}")
except Exception as e:
    print(f"  [FAIL] Erreur HarnessEngine : {e}")
    sys.exit(1)

# 4. Test Window Manager & Applications Ouvertes
print("\n[4/4] Test WindowManager (Universal App Tracking)...")
t0 = time.time()
try:
    from island.window_manager import AppWindowManager
    wm = AppWindowManager()
    windows = wm.get_all_open_windows()
    print(f"  [OK] {len(windows)} fenêtres interactives détectées en {time.time() - t0:.4f}s :")
    for w in windows[:5]:
        print(f"    - [{w['status']}] {w['app_name']}: {w['title'][:40]}")
except Exception as e:
    print(f"  [FAIL] Erreur WindowManager : {e}")
    sys.exit(1)

print("\n=== TOUS LES TESTS D'INTEGRATION SONT 100% VALIDES ===")
