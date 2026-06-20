import os
import json
from datetime import datetime, timezone

SNOOZE_FILE = os.path.join(os.path.dirname(__file__), "snoozes.json")

def load_snoozes():
    if not os.path.exists(SNOOZE_FILE):
        return {}
    try:
        with open(SNOOZE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def is_snoozed(instance_id):
    snoozes = load_snoozes()
    if instance_id not in snoozes:
        return False
    
    expiry_str = snoozes[instance_id]
    try:
        expiry = datetime.fromisoformat(expiry_str)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
            
        current_time = datetime.now(timezone.utc)
        if current_time > expiry:
            return False
        return True
    except Exception:
        return False
