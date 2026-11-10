import time
from typing import Optional, List, Dict
from island.logos import get_app_logo

class NotificationItem:
    def __init__(self, id_val: int, app_name: str, title: str, message: str, color_hex: str):
        self.id = id_val
        self.app_name = app_name
        self.title = title
        self.message = message
        self.color_hex = color_hex
        self.timestamp = time.time()
        self.logo = get_app_logo(app_name, 34)

    @property
    def time_str(self) -> str:
        diff = int(time.time() - self.timestamp)
        if diff < 60:
            return "À l'instant"
        elif diff < 3600:
            return f"Il y a {diff // 60} min"
        else:
            return f"Il y a {diff // 3600} h"

class NotificationManager:
    """
    Gestionnaire d'historique et carrousel scrollable de notifications pour Antigravity Island.
    - Conserve l'historique chronologique des notifications (WhatsApp, Telegram, Discord, etc.).
    - Permet de faire défiler les notifications une par une (scroll souris ou boutons).
    - Permet d'effacer toutes les notifications d'un coup (« Effacer tout ») ou une par une.
    """
    def __init__(self, max_items: int = 50):
        self.max_items = max_items
        self.items: List[NotificationItem] = []
        self.current_index = 0
        self._next_id = 1

    def add(self, app_name: str, title: str, message: str, color_hex: str) -> NotificationItem:
        # Éviter les doublons stricts consécutifs
        if self.items:
            last = self.items[0]
            if last.app_name == app_name and last.title == title and last.message == message:
                return last

        item = NotificationItem(self._next_id, app_name, title, message, color_hex)
        self._next_id += 1
        self.items.insert(0, item)  # Les plus récentes au début
        if len(self.items) > self.max_items:
            self.items.pop()
        self.current_index = 0
        return item

    def get_current(self) -> Optional[NotificationItem]:
        if not self.items:
            return None
        if self.current_index >= len(self.items):
            self.current_index = len(self.items) - 1
        if self.current_index < 0:
            self.current_index = 0
        return self.items[self.current_index]

    def next(self) -> Optional[NotificationItem]:
        if not self.items:
            return None
        if self.current_index < len(self.items) - 1:
            self.current_index += 1
        else:
            self.current_index = 0  # Boucle carrousel
        return self.get_current()

    def prev(self) -> Optional[NotificationItem]:
        if not self.items:
            return None
        if self.current_index > 0:
            self.current_index -= 1
        else:
            self.current_index = len(self.items) - 1  # Boucle carrousel
        return self.get_current()

    def clear_all(self):
        self.items.clear()
        self.current_index = 0

    def clear_current(self):
        if not self.items:
            return
        if 0 <= self.current_index < len(self.items):
            self.items.pop(self.current_index)
            if self.current_index >= len(self.items) and self.items:
                self.current_index = len(self.items) - 1

    def count(self) -> int:
        return len(self.items)
