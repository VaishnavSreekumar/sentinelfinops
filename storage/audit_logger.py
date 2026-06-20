import os
import json
from datetime import datetime, timezone

AUDIT_FILE = os.path.join(os.path.dirname(__file__), "audit_log.json")

def log_action(instance_id, action):
    if os.path.exists(AUDIT_FILE):
        try:
            with open(AUDIT_FILE, "r") as f:
                logs = json.load(f)
        except Exception:
            logs = []
    else:
        logs = []

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    entry = {
        "instance_id": instance_id,
        "action": action,
        "timestamp": timestamp
    }
    logs.append(entry)

    with open(AUDIT_FILE, "w") as f:
        json.dump(logs, f, indent=4)
