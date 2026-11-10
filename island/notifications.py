import os
import time
import sqlite3
import threading
import xml.etree.ElementTree as ET
from PyQt6.QtCore import QObject, pyqtSignal

class WindowsNotificationListener(QObject):
    """
    Écouteur haute performance des notifications Windows Toast en temps réel (WhatsApp, Telegram, Discord, etc.).
    Surveille la base de données système Windows Notifications (wpndatabase.db) en lecture seule (URI mode=ro).
    Dès qu'une notification système apparaît, elle est transmise à l'encoche dynamique pour un affichage style iPhone Dynamic Island.
    """
    notification_received = pyqtSignal(str, str, str, str)  # (app_name, title, message, color_hex)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.thread = None
        self.db_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Notifications\wpndatabase.db")
        self.last_seen_id = self._get_initial_max_id()

    def _get_initial_max_id(self) -> int:
        if not os.path.exists(self.db_path):
            return 0
        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=2.0)
            c = conn.cursor()
            c.execute("SELECT MAX(Id) FROM Notification")
            row = c.fetchone()
            conn.close()
            return row[0] if (row and row[0]) else 0
        except Exception:
            return 0

    def start(self):
        if self.running or not os.path.exists(self.db_path):
            return
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        print("[NotificationListener] Surveillance active des notifications Windows.")

    def stop(self):
        self.running = False

    def _parse_payload(self, payload) -> tuple[str, str]:
        if not payload:
            return "", ""
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="replace")
        try:
            root = ET.fromstring(payload)
            texts = [elem.text.strip() for elem in root.iter("text") if elem.text and elem.text.strip()]
            if len(texts) == 1:
                return "", texts[0]
            elif len(texts) >= 2:
                return texts[0], texts[1]
        except Exception:
            pass
        return "", ""

    def _get_app_info(self, primary_id: str, title: str) -> tuple[str, str]:
        pid = (primary_id or "").lower()
        if "whatsapp" in pid or "whatsapp" in title.lower():
            return "WhatsApp", "#25D366"
        elif "telegram" in pid or "telegram" in title.lower():
            return "Telegram", "#229ED9"
        elif "discord" in pid or "discord" in title.lower():
            return "Discord", "#5865F2"
        elif "slack" in pid:
            return "Slack", "#E01E5A"
        elif "chrome" in pid:
            return "Google Chrome", "#EA4335"
        elif "edge" in pid or "msedge" in pid:
            return "Microsoft Edge", "#0078D7"
        elif "outlook" in pid:
            return "Outlook", "#0078D4"
        elif "antigravity" in pid:
            return "Antigravity", "#38BDF8"
        
        # Nom par défaut nettoyé
        clean_name = primary_id.split("!")[-1].replace(".exe", "").capitalize() if primary_id else "Notification"
        if len(clean_name) > 20:
            clean_name = clean_name[:18] + ".."
        return clean_name, "#38BDF8"

    def _poll_loop(self):
        while self.running:
            time.sleep(0.4)
            if not os.path.exists(self.db_path):
                continue
            try:
                conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=1.5)
                c = conn.cursor()
                c.execute("""
                    SELECT N.Id, H.PrimaryId, N.Payload
                    FROM Notification N
                    LEFT JOIN NotificationHandler H ON N.HandlerId = H.RecordId
                    WHERE N.Id > ? AND N.Payload IS NOT NULL
                    ORDER BY N.Id ASC
                """, (self.last_seen_id,))
                
                rows = c.fetchall()
                conn.close()

                for nid, handler, payload in rows:
                    if nid > self.last_seen_id:
                        self.last_seen_id = nid
                    title, msg = self._parse_payload(payload)
                    if title or msg:
                        app_name, color = self._get_app_info(handler, title)
                        print(f"[NotificationListener] Nouvelle notification : [{app_name}] {title} - {msg}")
                        self.notification_received.emit(app_name, title, msg, color)

            except Exception as e:
                # Éviter de saturer la console si la base est brièvement verrouillée en écriture par Windows
                time.sleep(0.2)
