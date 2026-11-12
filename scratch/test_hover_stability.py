import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QMouseEvent, QEnterEvent

def test_hover_and_window_preview_stability():
    app = QApplication.instance() or QApplication(sys.argv)
    from island.window import IslandWindow
    w = IslandWindow()
    w.show()

    assert w.current_state == "idle"

    # 1. Simuler l'entrée du curseur
    ev_enter = QEnterEvent(QPointF(20, 20), QPointF(20, 20), QPointF(20, 20))
    w.enterEvent(ev_enter)
    assert w.current_state == "minimized_dock"
    assert len(w.open_windows) > 0, "Doit détecter les fenêtres ouvertes via EnumDesktopWindows"
    w.repaint()

    # 2. Simuler le survol des différentes tuiles
    for i in range(min(5, len(w.open_windows))):
        pos_x = 40.0 + i * 44.0 + 10.0
        ev_m = QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(pos_x, 25), Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        w.mouseMoveEvent(ev_m)
        w.repaint()

    # 3. Simuler le mouvement vers le haut de l'encoche pour ouvrir le Super Hub
    ev_up1 = QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(100, 10), Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    w.mouseMoveEvent(ev_up1)
    ev_up2 = QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(100, 8), Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    w.mouseMoveEvent(ev_up2)
    assert w.current_state == "control_hub", "Le survol vers le haut doit déployer le Super Hub"
    w.repaint()

    # 4. Simuler la sortie avec debounce
    w.leaveEvent(None)
    assert w.leave_debounce_timer.isActive(), "Le debounce timer doit être actif pour éviter l'oscillation"

    w.close()
    print("ALL HOVER & WINDOW PREVIEW TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_hover_and_window_preview_stability()
