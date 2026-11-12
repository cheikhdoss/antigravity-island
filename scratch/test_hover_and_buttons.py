# test_hover_and_buttons.py - Automated verification of hover stability and dedicated Island buttons
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QMouseEvent, QPainter, QPixmap

def main():
    print("=" * 60)
    print("TEST INTERFACE ISLAND : HOVER ANTI-SACCADE & BOUTONS DÉDIÉS")
    print("=" * 60)

    app = QApplication.instance() or QApplication(sys.argv)
    from island.window import IslandWindow

    window = IslandWindow.get_instance() or IslandWindow()
    window.show()

    # 1. Rendu et calcul des boutons en mode IDLE
    window.set_state("idle")
    print(f"[1] État initial : {window.current_state}")
    assert window.current_state == "idle"

    # Forcer le dessin sur un pixmap de test pour calculer les rects
    pix = QPixmap(300, 100)
    painter = QPainter(pix)
    test_rect = QRectF(24.0, 0.0, 148.0, 32.0)
    window._draw_idle_content(painter, test_rect)
    painter.end()

    print(f"    Bouton Ask / Mic Rect : {window.btn_manual_ask_rect}")
    print(f"    Bouton Expand Rect    : {window.btn_expand_rect}")
    assert not window.btn_manual_ask_rect.isEmpty(), "Le bouton Demander (Micro) doit être présent en mode idle"
    assert not window.btn_expand_rect.isEmpty(), "Le bouton Expand doit être présent en mode idle"

    # 2. Test du Clic sur le Bouton Manuel 'Demander' (Microphone)
    print("\n[2] Test du déclenchement manuel via le bouton Micro")
    window.trigger_manual_ask()
    print(f"    État après trigger_manual_ask : {window.current_state}")
    assert window.current_state == "listening", "L'Island doit passer en état listening lors du clic sur le micro"

    # Test de fin d'écoute manuelle
    window.stop_manual_ask()
    print(f"    État après stop_manual_ask : {window.current_state}")
    assert window.current_state == "thinking", "L'Island doit passer en état thinking après l'écoute"

    # 3. Test du Bouton d'Expansion Latérale vers le Super Hub
    print("\n[3] Test de l'expansion explicite via le bouton Dédié")
    window.set_state("idle")
    painter = QPainter(pix)
    window._draw_idle_content(painter, test_rect)
    painter.end()

    # Simuler le clic gauche sur btn_expand_rect
    center_expand = window.btn_expand_rect.center()
    click_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        center_expand,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    window.mousePressEvent(click_event)
    print(f"    État après clic bouton Expand : {window.current_state}")
    assert window.current_state == "control_hub", "L'Island doit s'étendre en Super Hub lors du clic sur Expand"

    # 4. Vérification des éléments dans le Super Hub (Control Hub)
    window.cur_w = 700.0
    window.cur_h = 280.0
    pix_hub = QPixmap(800, 350)
    painter_hub = QPainter(pix_hub)
    test_hub_rect = QRectF(24.0, 0.0, 700.0, 280.0)
    window._draw_control_hub_content(painter_hub, test_hub_rect)
    painter_hub.end()

    print(f"\n[4] Vérification des éléments du Control Hub :")
    print(f"    Bouton Demander (Hub)  : {window.btn_manual_ask_rect}")
    print(f"    Bouton Collapse (Hub)  : {window.btn_collapse_rect}")
    print(f"    Bouton Screenshot      : {window.btn_screenshot_rect}")
    print(f"    Bouton Bureau          : {window.btn_desktop_rect}")
    print(f"    Bouton Réglages        : {window.btn_settings_rect}")
    print(f"    Bouton Effacer Notifs  : {window.btn_clear_notifs_rect}")

    assert not window.btn_manual_ask_rect.isEmpty(), "Le bouton Demander doit être présent dans le Hub"
    assert not window.btn_collapse_rect.isEmpty(), "Le bouton de repli doit être présent dans le Hub"
    assert not window.btn_screenshot_rect.isEmpty(), "Le bouton Screenshot doit être présent"
    assert not window.btn_desktop_rect.isEmpty(), "Le bouton Bureau doit être présent"

    # 5. Test du Clic sur le Bouton de Repli (Collapse)
    print("\n[5] Test du repli via le bouton Collapse")
    center_collapse = window.btn_collapse_rect.center()
    click_col_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        center_collapse,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    window.mousePressEvent(click_col_event)
    print(f"    État après clic bouton Collapse : {window.current_state}")
    assert window.current_state == "idle", "L'Island doit se replier en idle lors du clic sur Collapse"

    # 6. Test de Stabilité Hover Anti-Saccade
    print("\n[6] Test de la stabilisation du survol haut (Hover Anti-Saccade)")
    window.set_state("minimized_dock")
    assert window.hover_expand_timer is not None, "Le timer hover_expand_timer doit exister"
    assert not window.hover_expand_timer.isActive(), "Le timer ne doit pas être actif initialement"

    # Simuler le curseur en haut (y <= 14)
    move_top = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(50.0, 10.0),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    window.mouseMoveEvent(move_top)
    assert window.hover_expand_timer.isActive(), "Le timer d'expansion intentionnelle doit s'activer à y <= 14"

    # Simuler le curseur redescendant (y > 14) -> annulation immédiate de l'expansion accidentelle
    move_down = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(50.0, 30.0),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    window.mouseMoveEvent(move_down)
    assert not window.hover_expand_timer.isActive(), "Le timer doit être stoppé si le curseur redescend"

    window.close()
    print("\n" + "=" * 60)
    print("TOUS LES TESTS D'INTERFACE SONT VALIDÉS AVEC SUCCÈS ! (100% OK)")
    print("=" * 60)

if __name__ == "__main__":
    main()
