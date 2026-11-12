import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QMouseEvent

# Initialiser l'application Qt headless pour le test
app = QApplication.instance() or QApplication(sys.argv)

from island.config import Config
from island.window import IslandWindow

def test_keyboard_prompt_feature():
    print("=== DÉBUT DU TEST UNITAIRE : KEYBOARD PROMPT SUR ANTIGRAVITY ISLAND ===")
    
    # 1. Vérification de la configuration Config.STATES
    assert "prompt_input" in Config.STATES, "L'état 'prompt_input' doit exister dans Config.STATES"
    cfg = Config.STATES["prompt_input"]
    assert cfg.width == 480 and cfg.height == 52 and cfg.radius == 26
    print("✓ Config.STATES['prompt_input'] correctement configuré (480x52, r=26)")

    # 2. Instanciation de IslandWindow
    win = IslandWindow()
    win.show()
    app.processEvents()

    assert win.custom_idle_w == 110.0, f"Largeur idle attendue 110, trouvé: {win.custom_idle_w}"
    assert hasattr(win, "prompt_input"), "IslandWindow doit posséder un child widget prompt_input"
    assert not win.prompt_input.isVisible(), "prompt_input doit être masqué en mode idle"
    print("✓ IslandWindow instancié au repos (idle épuré) avec prompt_input masqué")

    # 3. Test du déclenchement trigger_keyboard_ask()
    win.trigger_keyboard_ask()
    app.processEvents()
    time.sleep(0.05)
    app.processEvents()

    assert win.current_state == "prompt_input", f"État attendu 'prompt_input', actuel: {win.current_state}"
    assert win.target_w == 480.0 and win.target_h == 52.0
    print("✓ trigger_keyboard_ask() bascule correctement l'Island en mode 'prompt_input'")

    # 4. Vérification du layout et du child widget prompt_input
    pill_rect = QRectF(Config.SHADOW_BLUR + 16.0, 0.0, win.target_w, win.target_h)
    from PyQt6.QtGui import QPainter, QPixmap
    pix = QPixmap(int(win.width()), int(win.height()))
    painter = QPainter(pix)
    win._draw_prompt_input_content(painter, pill_rect)
    painter.end()
    app.processEvents()

    assert win.prompt_input.isVisible(), "prompt_input doit être visible en mode prompt_input"
    assert win.btn_prompt_send_rect.isValid(), "btn_prompt_send_rect doit être initialisé"
    assert win.btn_prompt_cancel_rect.isValid(), "btn_prompt_cancel_rect doit être initialisé"
    print("✓ Rendu _draw_prompt_input_content exécuté sans erreur, boutons d'envoi et d'annulation valides")

    # 5. Test de l'annulation via touche Escape
    win._on_prompt_escape()
    app.processEvents()
    time.sleep(0.05)
    app.processEvents()

    assert win.current_state == "idle", f"État attendu 'idle' après Escape, actuel: {win.current_state}"
    assert not win.prompt_input.isVisible(), "prompt_input doit être masqué après Escape"
    print("✓ Annulation Escape / _on_prompt_escape() replie proprement l'Island en mode 'idle'")

    # 6. Test de saisie et de soumission
    win.trigger_keyboard_ask()
    app.processEvents()
    win.prompt_input.setText("Quelle heure est-il ?")
    assert win.prompt_input.text() == "Quelle heure est-il ?"
    
    # Simuler soumission
    win._on_prompt_input_submitted()
    app.processEvents()

    assert win.current_state in ["thinking", "speaking"], f"État attendu 'thinking' ou 'speaking' après soumission, actuel: {win.current_state}"
    assert not win.prompt_input.isVisible(), "prompt_input doit être masqué pendant le traitement"
    print("✓ Soumission textuelle validée : bascule immédiate en état d'analyse/réponse")

    # Attendre que la réponse textuelle arrive (speaking)
    for _ in range(30):
        app.processEvents()
        time.sleep(0.05)
        if win.current_state == "speaking":
            break
    print(f"✓ Réponse générée et affichée dans l'état : {win.current_state} (message: '{win.message_text[:40]}...')")

    # 7. Test clic sur bouton clavier au hover (minimized_dock)
    win.set_state("minimized_dock")
    win.reading_timer.stop()
    app.processEvents()
    # Forcer rendu minimized_dock pour positionner btn_keyboard_ask_rect
    painter = QPainter(pix)
    win._draw_minimized_dock_content(painter, QRectF(Config.SHADOW_BLUR + 16.0, 0.0, win.target_w, win.target_h))
    painter.end()

    assert win.btn_keyboard_ask_rect.isValid() and not win.btn_keyboard_ask_rect.isEmpty()
    kb_click_pos = win.btn_keyboard_ask_rect.center()
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        kb_click_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    win.mousePressEvent(event)
    app.processEvents()
    time.sleep(0.05)
    app.processEvents()

    assert win.current_state == "prompt_input", f"Clic sur l'icône clavier au hover doit ouvrir 'prompt_input', actuel: {win.current_state}"
    print("✓ Clic sur l'icône de clavier vectorielle au hover déclenche parfaitement la saisie clavier")

    win.close()
    print("=== TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS (100% OK) ===")

if __name__ == "__main__":
    test_keyboard_prompt_feature()
