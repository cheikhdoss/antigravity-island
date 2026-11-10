import sqlite3
import os
import xml.etree.ElementTree as ET

db_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Notifications\wpndatabase.db")

try:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute("""
        SELECT N.Id, N.ArrivalTime, H.PrimaryId, N.Type, N.Payload
        FROM Notification N
        LEFT JOIN NotificationHandler H ON N.HandlerId = H.RecordId
        ORDER BY N.ArrivalTime DESC
        LIMIT 5
    """)
    rows = c.fetchall()
    for row in rows:
        nid, arr, handler, ntype, payload = row
        print(f"--- ID: {nid} | App: {handler} | Time: {arr} ---")
        if payload:
            try:
                # Payload can be XML or bytes
                if isinstance(payload, bytes):
                    # In Windows 10/11, payload is often UTF-8 or UTF-16 XML
                    text = payload.decode("utf-8", errors="replace")
                else:
                    text = str(payload)
                print("Payload preview:", text[:200])
            except Exception as e:
                print("Decode error:", e)
except Exception as e:
    print("Error:", e)
