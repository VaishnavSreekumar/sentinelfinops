from flask import Flask, request, jsonify
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
        import boto3
        from scanner.config import AWS_REGION, SNOOZE_TABLE

        expiration_dt = datetime.now(timezone.utc) + timedelta(hours=24)
        expiration = expiration_dt.strftime("%Y-%m-%dT%H:%M:%S")
        ttl = int(expiration_dt.timestamp())

        try:
            dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
            table = dynamodb.Table(SNOOZE_TABLE)
            table.put_item(
                Item={
                    "instance_id": instance_id,
                    "expiry_timestamp": expiration,
                    "ttl": ttl
                }
            )
        except Exception as e:
            print(f"Error saving snooze to DynamoDB: {e}")

        return jsonify({
            "text": f"Instance {instance_id} snoozed for 24h"
        }), 200

    elif action == "acknowledge":
        from storage.audit_logger import log_action
        log_action(instance_id, "acknowledged")

        from storage.alert_state_manager import set_alert_state
        set_alert_state(instance_id, "ACKNOWLEDGED")

        return jsonify({
            "text": f"Instance {instance_id} acknowledged"
        }), 200

    return {
        "text": f"Action '{action}' recorded for {instance_id}"
    }

if __name__ == "__main__":
    app.run(port=5000)