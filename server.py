from flask import Flask, request
import json
import os
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

@app.route("/slack/actions", methods=["POST"])
def actions():

    payload = json.loads(
        request.form["payload"]
    )

    action = payload["actions"][0]["action_id"]
    instance_id = payload["actions"][0]["value"]

    print("\n=== BUTTON CLICK ===")
    print("Action:", action)
    print("Instance:", instance_id)

    if action == "snooze":
        snoozes_file = os.path.join(os.path.dirname(__file__), "storage", "snoozes.json")
        try:
            with open(snoozes_file, "r") as f:
                snoozes = json.load(f)
        except Exception:
            snoozes = {}

        expiration = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
        snoozes[instance_id] = expiration

        with open(snoozes_file, "w") as f:
            json.dump(snoozes, f, indent=4)

        return {
            "text": f"⏰ Instance {instance_id} snoozed for 24h"
        }

    elif action == "acknowledge":
        from storage.audit_logger import log_action
        log_action(instance_id, "acknowledged")

        return {
            "text": f"✅ Instance {instance_id} acknowledged"
        }

    return {
        "text": f"Action '{action}' recorded for {instance_id}"
    }

if __name__ == "__main__":
    app.run(port=5000)