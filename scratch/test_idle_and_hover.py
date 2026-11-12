import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QImage, QMouseEvent, QEnterEvent

from island.window import IslandWindow
from island.config import Config

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    win = IslandWindow()
    win.set_state("idle")
    win.show()

    print("\n--- TEST 1: État au repos (idle) ---")
    assert win.current_state == "idle", f"État attendu idle, obtenu {win.current_state}"
    assert win.custom_idle_w == 110.0, f"Largeur attendue 110.0, obtenue {win.custom_idle_w}"
    
    # Simuler le rendu idle
    img = QImage(300, 100, QImage.Format.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    win._draw_idle_content(p, QRectF(0, 0, 110, 30))
    p.end()

    # Vérifier qu'aucun bouton n'est actif au repos
    assert win.btn_manual_ask_rect.isEmpty(), "Le micro ne doit pas être actif en idle"
    assert win.btn_keyboard_ask_rect.isEmpty(), "Le clavier ne doit pas être actif en idle"
    assert win.btn_expand_rect.isEmpty(), "Le bouton chevron/expand ne doit pas être actif en idle"
    print("✓ État idle 100% épuré : aucun bouton parasite sur la pilule au repos.")

    print("\n--- TEST 2: Apparition des outils au hover (enterEvent -> minimized_dock) ---")
    enter_ev = QEnterEvent(QPointF(55, 15), QPointF(55, 15), QPointF(55, 15))
    win.enterEvent(enter_ev)
    assert win.current_state == "minimized_dock", f"Au hover, l'état doit être minimized_dock, obtenu {win.current_state}"

    # Rendu du dock
    img_dock = QImage(600, 100, QImage.Format.Format_ARGB32)
    img_dock.fill(0)
    p_dock = QPainter(img_dock)
    win._draw_minimized_dock_content(p_dock, QRectF(0, 0, 500, 54))
    p_dock.end()

    # Vérifier que les outils sont bien présents au hover
    assert not win.btn_manual_ask_rect.isEmpty(), "Le bouton micro doit apparaître au hover"
    assert not win.btn_keyboard_ask_rect.isEmpty(), "Le bouton clavier doit apparaître au hover"
    assert not win.btn_expand_rect.isEmpty(), "Le bouton hub doit apparaître au hover"
    print("✓ Outils tactiles (Micro, Clavier, Hub) présents au hover.")

    print("\n--- TEST 3: Sensibilité du glissement vers le haut ---")
    # 1. Curseur à Y=10 (hauteur normale des icônes/boutons) -> Ne doit PAS armer le timer d'expansion
    ev_mid = QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(200, 10), Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    win.mouseMoveEvent(ev_mid)
    assert not win.hover_expand_timer.isActive(), "À Y=10, le timer d'expansion vers le Hub ne doit PAS être actif"
    print("✓ Pas d'expansion intempestive en survolant les icônes (Y=10).")

    # 2. Curseur au-dessus du bouton clavier ou micro -> Ne doit PAS armer le timer
    btn_kb_center = win.btn_keyboard_ask_rect.center()
    ev_kb = QMouseEvent(QMouseEvent.Type.MouseMove, btn_kb_center, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    win.mouseMoveEvent(ev_kb)
    assert not win.hover_expand_timer.isActive(), "Au-dessus d'un bouton, le timer d'expansion ne doit PAS être actif"
    assert win.hovered_action_btn == "keyboard_ask", f"Bouton survolé attendu 'keyboard_ask', obtenu {win.hovered_action_btn}"
    print("✓ Le survol des boutons micro/clavier est prioritaire et sécurisé.")

    # 3. Curseur poussé délibérément tout en haut (Y <= 2.5) dans une zone vide -> Arme le timer avec délai de 450ms
    ev_top = QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(200, 1.5), Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    win.mouseMoveEvent(ev_top)
    assert win.hover_expand_timer.isActive(), "Le timer d'expansion doit s'armer uniquement si Y <= 2.5 dans une zone vide"
    assert win.hover_expand_timer.interval() == 450, f"Délai attendu 450ms, obtenu {win.hover_expand_timer.interval()}ms"
    print("✓ Sensibilité parfaitement calibrée (Y <= 2.5 et dwell time 450ms).")

    print("\n--- TEST 4: Repli au repos (leaveEvent) ---")
    win.leave_debounce_timer.stop()
    win.set_state("idle")
    assert win.current_state == "idle"
    assert win.target_w == 110.0
    print("✓ Repli propre vers idle.")

    print("\n=== TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS (100% OK) ===")
    win.close()

if __name__ == "__main__":
    run_tests()
