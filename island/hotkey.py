import time
import threading
from pynput import keyboard

class PushToTalkEngine:
    """
    Moteur Push-to-Talk global avec combinaison de touches Windows + Alt.
    Détecte les touches n'importe où sous Windows, même si l'application est en arrière-plan.
    Supporte les modes Hybride, Maintien (Hold) et Bascule (Toggle).
    """

    def __init__(self, window_instance, mode: str = "hybrid"):
        self.window = window_instance
        self.mode = mode
        self.listener = None
        self.running = False
        
        self.win_pressed = False
        self.alt_pressed = False
        self.press_start_time = 0.0
        self.is_active = False
        self._lock = threading.Lock()

    def start(self):
        if self.running:
            return
        self.running = True
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.daemon = True
        self.listener.start()
        print("[PushToTalkEngine] Raccourci global active : [Windows + Alt]")

    def stop(self):
        self.running = False
        if self.listener:
            self.listener.stop()
            self.listener = None

    def set_mode(self, mode: str):
        self.mode = mode

    def _is_win_key(self, key):
        return key in [keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r]

    def _is_alt_key(self, key):
        return key in [keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr]

    def _on_press(self, key):
        with self._lock:
            if self._is_win_key(key):
                self.win_pressed = True
            elif self._is_alt_key(key):
                self.alt_pressed = True

            # Détection de la combinaison Windows + Alt
            if self.win_pressed and self.alt_pressed:
                if self.press_start_time == 0.0:
                    self.press_start_time = time.time()
                    self._handle_combo_down()

    def _on_release(self, key):
        with self._lock:
            was_combo_active = self.win_pressed and self.alt_pressed
            
            if self._is_win_key(key):
                self.win_pressed = False
            elif self._is_alt_key(key):
                self.alt_pressed = False

            # Relâchement de l'une des touches
            if was_combo_active and not (self.win_pressed and self.alt_pressed):
                press_duration = time.time() - self.press_start_time
                self.press_start_time = 0.0
                self._handle_combo_up(press_duration)

    def _handle_combo_down(self):
        if self.mode == "hold":
            self.is_active = True
            print("[PushToTalk] Maintien [Windows + Alt] -> Mode Ecoute...")
            self.window.state_change_requested.emit("set_state", {"state": "listening"})
        elif self.mode == "toggle":
            pass
        else:  # hybrid
            if not self.is_active:
                print("[PushToTalk] Combinaison [Windows + Alt] pressee...")
                self.window.state_change_requested.emit("set_state", {"state": "listening"})

    def _trigger_thinking_and_capture(self):
        self.window.state_change_requested.emit("set_state", {"state": "thinking"})
        threading.Thread(target=self._capture_screen_async, daemon=True).start()

    def _capture_screen_async(self):
        try:
            from island.vision import capture_screen
            capture_screen()
            print("[PushToTalk] Capture d'ecran automatique effectuee en arriere-plan (screen_latest.png)")
        except Exception as e:
            print("[PushToTalk] Erreur capture d'ecran:", e)

    def _handle_combo_up(self, duration: float):
        if self.mode == "hold":
            self.is_active = False
            print(f"[PushToTalk] Relachement apres {duration:.2f}s -> Passage en Analyse...")
            self._trigger_thinking_and_capture()
        elif self.mode == "toggle":
            if self.is_active:
                self.is_active = False
                print("[PushToTalk] Bascule off -> Passage en Analyse...")
                self._trigger_thinking_and_capture()
            else:
                self.is_active = True
                print("[PushToTalk] Bascule on -> Mode Ecoute...")
                self.window.state_change_requested.emit("set_state", {"state": "listening"})
        else:  # hybrid
            if duration < 0.40:
                # Tap court : bascule
                if self.is_active:
                    self.is_active = False
                    print("[PushToTalk] Tap court -> Fin d'ecoute, Analyse...")
                    self._trigger_thinking_and_capture()
                else:
                    self.is_active = True
                    print("[PushToTalk] Tap court -> Activation mode Ecoute...")
                    self.window.state_change_requested.emit("set_state", {"state": "listening"})
            else:
                # Maintien long : Push-to-Talk
                self.is_active = False
                print(f"[PushToTalk] Relachement maintien ({duration:.2f}s) -> Analyse...")
                self._trigger_thinking_and_capture()
