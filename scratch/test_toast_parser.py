import sqlite3
import os
import xml.etree.ElementTree as ET
import time

db_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Notifications\wpndatabase.db")

def parse_toast(xml_str):
    try:
        root = ET.fromstring(xml_str)
        texts = [elem.text for elem in root.iter("text") if elem.text]
        title = texts[0] if len(texts) > 0 else ""
        msg = texts[1] if len(texts) > 1 else ""
        return title, msg
    except Exception:
        return "", ""

conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
c = conn.cursor()
c.execute("""
    SELECT N.Id, H.PrimaryId, N.Payload
    FROM Notification N
    LEFT JOIN NotificationHandler H ON N.HandlerId = H.RecordId
    WHERE N.Payload IS NOT NULL
    ORDER BY N.Id DESC
    LIMIT 10
""")

for nid, handler, payload in c.fetchall():
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="replace")
    title, msg = parse_toast(payload)
    if title or msg:
        print(f"ID {nid} | App: {handler} | Title: {title} | Msg: {msg}")
