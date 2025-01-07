import sqlite3
import os
import datetime
from typing import List, Dict, Any
# from parsers import parse_text_response

DATABASE_FILE = os.path.join(os.path.dirname(__file__), "message_history.db")

def load_message_history() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT message_type, content, timestamp, session_id, id FROM messages ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip(["message_type", "content", "timestamp", "session_id", "id"], row)) for row in rows]

def update_message_history(messages: List[Dict[str, str]]) -> None:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (timestamp) VALUES (?)", (datetime.datetime.now().isoformat(),))
    session_id = cursor.lastrowid
    for message in messages:
        # content = parse_llm_response(message["content"])
        content = message["content"]
        if content:
            message_type = "request_info" if "request_info" in content else \
                           "task_complete" if "task_complete" in content else \
                           "action"
            timestamp = datetime.datetime.now().isoformat()
            cursor.execute("INSERT INTO messages (message_type, content, timestamp, session_id) VALUES (?, ?, ?, ?)",
                           (message_type, content, timestamp, session_id))
    conn.commit()
    conn.close()