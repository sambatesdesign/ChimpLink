# log_utils.py

from datetime import datetime
from config import LOG_FILE
from storage_utils import load_json, save_json

def append_log_entry(event, email, status, diff=None, payload=None):
    log = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "email": email,
        "status": status
    }
    if diff:
        log["changes"] = diff
    if payload:
        log["payload"] = payload

    logs = load_json(LOG_FILE)
    logs.append(log)
    save_json(LOG_FILE, logs)
