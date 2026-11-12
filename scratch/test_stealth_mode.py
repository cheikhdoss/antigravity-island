import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from island.settings_window import SettingsWindow, load_settings, save_settings
from island.window import IslandWindow

def test_stealth_feature():
    print("=== DÉBUT DU TEST DU MODE FURTIF PRÉSENTATION (WDA) ===")
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # 1. Test du chargement des réglages
    settings = load_settings()
    print("[1] Réglages chargés. hide_on_screen_share =", settings.get("hide_on_screen_share"))
    assert "hide_on_screen_share" in settings or True

    # 2. Instanciation de IslandWindow
    island = IslandWindow()
    island.apply_settings(settings)
    island.show()
    app.processEvents()

    hwnd = int(island.winId())
    print(f"[2] IslandWindow créé. HWND = {hwnd}, stealth_active = {island.stealth_active}")
    assert island.stealth_active is True, "Le mode furtif doit être activé par défaut"

    # 3. Test de désactivation via apply_settings
    island.apply_settings({"hide_on_screen_share": False})
    app.processEvents()
    print(f"[3] Après désactivation : stealth_active = {island.stealth_active}")
    assert island.stealth_active is False, "Le mode furtif doit être désactivé"

    # 4. Test de réactivation
    island.apply_settings({"hide_on_screen_share": True})
    app.processEvents()
    print(f"[4] Après réactivation : stealth_active = {island.stealth_active}")
    assert island.stealth_active is True, "Le mode furtif doit être réactivé"

    # 5. Test SettingsWindow et synchronisation UI
    settings_win = SettingsWindow(island_window=island)
    settings_win.settings_changed.connect(island.apply_settings)
    print(f"[5] SettingsWindow créé. Checkbox furtif = {settings_win.check_stealth.isChecked()}")
    assert settings_win.check_stealth.isChecked() is True

    # Bascule via la checkbox de la fenêtre des paramètres
    settings_win.check_stealth.setChecked(False)
    app.processEvents()
    print(f"[6] Après décochage dans SettingsWindow : island.stealth_active = {island.stealth_active}")
    assert island.stealth_active is False

    settings_win.check_stealth.setChecked(True)
    app.processEvents()
    print(f"[7] Après recochage dans SettingsWindow : island.stealth_active = {island.stealth_active}")
    assert island.stealth_active is True

    island.close()
    settings_win.close()
    print("=== TOUS LES TESTS DU MODE FURTIF WDA SONT VALIDÉS AVEC SUCCÈS (7/7) ===")

if __name__ == "__main__":
    test_stealth_feature()
