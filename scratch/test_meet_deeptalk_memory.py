import os
import sys
import time

# Ensure island is on sys.path
sys.path.insert(0, r"C:\Users\pro\.gemini\antigravity\scratch\antigravity-island")

from island.deeptalk import DeepTalk
from island.meet_listener import is_teacher_question

print("=== TEST MEMOIRE CONVERSATIONNELLE MULTI-TOURS DEEPTALK EN COURS MEET ===")

# 1. Verification des questions du professeur (question initiale + questions de suivi)
q1 = "c'est quoi une variable"
q2 = "dans quel cas on l'utilise"
q3 = "donne-moi un exemple"
q4 = "a quoi ca sert"

assert is_teacher_question(q1) is True, f"'{q1}' doit etre detectee"
assert is_teacher_question(q2) is True, f"'{q2}' doit etre detectee"
assert is_teacher_question(q3) is True, f"'{q3}' doit etre detectee"
assert is_teacher_question(q4) is True, f"'{q4}' doit etre detectee"
print("[1] Questions de suivi Meet : 100% DETECTEES")

# 2. Simulation de dialogue multi-tours
dt = DeepTalk.get_instance()
dt.clear()

# Tour 1 : Définition
a1 = "Une variable est un espace de stockage nomme en memoire qui contient une valeur modifiable."
dt.record_turn(q1, a1)
assert dt.count_turns() == 1
print("[2] Tour 1 enregistre : VALIDÉ")

# Tour 2 : Cas d'usage (avec pronom 'l'utilise')
summary_t2 = dt.get_context_summary_text(limit_turns=3)
assert "variable" in summary_t2.lower()
print("[3] Contexte DeepTalk Tour 2 : VALIDÉ")
a2 = "On l'utilise pour stocker des etats temporaires ou des resultats intermediaires dans le programme."
dt.record_turn(q2, a2)
assert dt.count_turns() == 2
print("[4] Tour 2 enregistre : VALIDÉ")

# Tour 3 : Exemple
summary_t3 = dt.get_context_summary_text(limit_turns=3)
assert "dans quel cas" in summary_t3.lower()
a3 = "Par exemple, en Python : compteur = 0 pour suivre le nombre d'iterations."
dt.record_turn(q3, a3)
assert dt.count_turns() == 3
print("[5] Tour 3 enregistre : VALIDÉ")

# 3. Test de persistance sur disque (redémarrage du PC)
time.sleep(0.1)
dt_reboot = DeepTalk(max_turns=10)
assert dt_reboot.count_turns() >= 3, f"Attendu >= 3 tours restaures, obtenu {dt_reboot.count_turns()}"
print(f"[6] Persistance disque JSON : {dt_reboot.count_turns()} tours restaures avec succes !")

print("=== TOUS LES TESTS DEEPTALK MULTI-TOURS SONT PASSES AVEC SUCCES (6/6) ===")
