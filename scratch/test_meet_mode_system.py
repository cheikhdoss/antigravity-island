import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from island.settings_window import SettingsWindow, load_settings, save_settings
from island.window import IslandWindow
from island.meet_listener import MeetListener, is_teacher_question, resample_to_16k_mono

def test_meet_system():
    print("=== DÉBUT DU TEST DU SYSTÈME COMPLET MODE MEET ===")
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # 1. Test des déclencheurs
    assert is_teacher_question("c'est quoi une passerelle par defaut ?") is True
    assert is_teacher_question("pourquoi dit-on que le protocole ip est non connecte") is True
    assert is_teacher_question("qu'est-ce que vous remarquez sur ce schema") is True
    assert is_teacher_question("quelle est la commande pour lister les conteneurs") is True
    assert is_teacher_question("on va maintenant etudier le routage dynamique") is False
    print("[1] Détection des questions du professeur : VALIDÉE")

    # 2. Test du rééchantillonnage audio
    import numpy as np
    raw_stereo_48k = np.zeros(48000 * 2, dtype=np.int16).tobytes()
    resampled = resample_to_16k_mono(raw_stereo_48k, 48000, 2)
    assert len(resampled) == 32000, f"Attendu 32000 octets, obtenu {len(resampled)}"
    print("[2] Rééchantillonnage 48kHz stéréo -> 16kHz mono : VALIDÉ")

    # 3. Test de l'IslandWindow et intégration MeetListener
    island = IslandWindow()
    island.show()
    app.processEvents()

    assert hasattr(island, "meet_listener"), "island doit posséder un meet_listener"
    assert hasattr(island, "btn_meet_rect"), "island doit posséder un btn_meet_rect"
    assert island.meet_active is False, "Le mode Meet doit être inactif au démarrage"
    print("[3] Intégration MeetListener dans IslandWindow : VALIDÉE")

    # 4. Test d'activation / désactivation
    island.set_meet_mode(True)
    app.processEvents()
    assert island.meet_active is True
    assert island.meet_listener.is_running is True
    print("[4] Activation du Mode Meet (Loopback Stream) : VALIDÉE")

    island.set_meet_mode(False)
    app.processEvents()
    assert island.meet_active is False
    assert island.meet_listener.is_running is False
    print("[5] Désactivation du Mode Meet : VALIDÉE")

    # 5. Test de synchronisation avec SettingsWindow
    settings_win = SettingsWindow(island_window=island)
    assert hasattr(settings_win, "check_meet_mode"), "SettingsWindow doit avoir check_meet_mode"
    
    settings_win.check_meet_mode.setChecked(True)
    app.processEvents()
    assert island.meet_active is True
    print("[6] Synchronisation SettingsWindow -> IslandWindow : VALIDÉE")

    settings_win.check_meet_mode.setChecked(False)
    app.processEvents()
    assert island.meet_active is False
    print("[7] Synchronisation extinction SettingsWindow : VALIDÉE")

    # 6. Test de détection de question et transition d'état
    test_q = "c'est quoi le masque de sous-réseau ?"
    island._on_meet_question_detected(test_q)
    app.processEvents()
    assert island.current_state == "thinking"
    assert "Question" in island.action_title
    print(f"[8] Transition d'état sur question professeur : VALIDÉE (State: {island.current_state}, Title: '{island.action_title}')")

    island.set_state("idle")
    island.close()
    settings_win.close()
    print("=== TOUS LES TESTS DU MODE MEET (8/8) SONT PASSÉS AVEC SUCCÈS ===")

if __name__ == "__main__":
    test_meet_system()
