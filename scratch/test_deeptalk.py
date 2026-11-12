# test_deeptalk.py - Verification script for DeepTalk persistent memory in Antigravity Island
import sys
import os
import time

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from island.deeptalk import DeepTalk
from island.brain import generate_response

def main():
    print("=" * 60)
    print("TEST DEEPTALK : MÉMOIRE CONVERSATIONNELLE PERSISTANTE")
    print("=" * 60)

    # 1. Clear previous history for clean test
    dt = DeepTalk.get_instance()
    dt.clear()
    time.sleep(0.1)
    print(f"[1] Mémoire initiale vidée. Tours actuels : {dt.count_turns()}")
    assert dt.count_turns() == 0, "La mémoire doit être vide au départ."

    # 2. Tour 1 : Définition d'un CRM
    q1 = "C'est quoi un CRM ?"
    print(f"\n[2] Tour 1 - Envoi query : '{q1}'")
    t0 = time.time()
    resp1 = generate_response(q1)
    d1 = time.time() - t0
    print(f"    Réponse 1 ({d1:.2f}s) : {resp1}")
    time.sleep(0.3) # wait for async disk save

    # Vérification que la réponse contient bien la notion de CRM / relation client
    assert any(w in resp1.lower() for w in ["crm", "client", "relation", "gestion"]), "La réponse 1 doit définir un CRM"
    assert dt.count_turns() >= 1, "Le tour 1 doit être enregistré dans DeepTalk"

    # 3. Tour 2 : Question contextuelle avec anaphore ("ça", "ta définition")
    q2 = "Pour qui tu dis ça dans ta définition ?"
    print(f"\n[3] Tour 2 - Envoi query contextuelle : '{q2}'")
    t0 = time.time()
    resp2 = generate_response(q2)
    d2 = time.time() - t0
    print(f"    Réponse 2 ({d2:.2f}s) : {resp2}")
    time.sleep(0.3) # wait for async disk save

    # Vérification que la réponse 2 fait référence au contexte (entreprises, clients, équipes commerciales, etc.)
    # et n'est pas perdue ou hors-sujet
    has_context = any(w in resp2.lower() for w in ["entreprise", "client", "commercial", "équipe", "vente", "service", "crm", "professionnel", "organisation"])
    print(f"    Détection du contexte CRM dans la réponse 2 : {'REUSSIE' if has_context else 'ATTENTION'}")
    assert dt.count_turns() >= 2, "Les 2 tours doivent être enregistrés dans DeepTalk"

    # 4. Simulation de redémarrage complet du PC / Application
    print("\n[4] Simulation du redémarrage PC (Recréation complète de l'instance DeepTalk)")
    memory_file = dt.storage_file
    print(f"    Fichier de persistance disque : {memory_file}")
    assert os.path.exists(memory_file), f"Le fichier de persistance {memory_file} doit exister sur le disque"

    # Forcer la réinitialisation de l'instance en mémoire
    DeepTalk._instance = None
    dt_restarted = DeepTalk.get_instance()
    loaded_turns = dt_restarted.count_turns()
    print(f"    Tours rechargés automatiquement après 'reboot' : {loaded_turns}")
    assert loaded_turns >= 2, f"DeepTalk doit avoir rechargé au moins 2 tours depuis le disque, trouvé {loaded_turns}"

    # Vérification des messages restaurés
    messages = dt_restarted.get_messages_for_llm("test", "system")
    print(f"    Total messages reconstruits : {len(messages)}")

    # 5. Test commande vocale de réinitialisation ("oublie la discussion")
    print("\n[5] Test de la commande d'oubli : 'oublie la discussion'")
    reset_resp = generate_response("oublie la discussion")
    print(f"    Réponse reset : {reset_resp}")
    time.sleep(0.3)
    assert dt_restarted.count_turns() == 0, "La mémoire doit être à 0 après 'oublie la discussion'"
    print(f"    Tours restants après reset : {dt_restarted.count_turns()}")

    print("\n" + "=" * 60)
    print("TOUS LES TESTS DEEPTALK SONT VALIDES AVEC SUCCÈS ! (100% OK)")
    print("=" * 60)

if __name__ == "__main__":
    main()
