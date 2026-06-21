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
    raw_value = payload["actions"][0]["value"]
    
    account_id = "Unknown"
    account_name = "Unknown"
    region = "Unknown"
    try:
        value_data = json.loads(raw_value)
        resource_type = value_data.get("resource_type", "EC2")
        resource_id = value_data.get("resource_id", raw_value)
        account_id = value_data.get("account_id", "Unknown")
        account_name = value_data.get("account_name", "Unknown")
        region = value_data.get("region", "Unknown")
    except Exception:
        if raw_value.startswith("vol-"):
            resource_type = "EBS"
        else:
            resource_type = "EC2"
        resource_id = raw_value

    print("\n=== BUTTON CLICK ===")
    print("Action:", action)
    print("Resource Type:", resource_type)
    print("Resource ID:", resource_id)
    print("Account:", account_name, f"({account_id})")
    print("Region:", region)

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
                    "instance_id": resource_id,
                    "expiry_timestamp": expiration,
                    "ttl": ttl
                }
            )
        except Exception as e:
            print(f"Error saving snooze to DynamoDB: {e}")

        msg_type = "Volume" if resource_type == "EBS" else "Instance"
        return jsonify({
            "text": f"{msg_type} {resource_id} snoozed for 24h"
        }), 200

    elif action == "acknowledge":
        from storage.audit_logger import log_action
        log_action(resource_id, "acknowledged", account_id, account_name, region)

        from storage.alert_state_manager import set_alert_state
        set_alert_state(resource_id, "ACKNOWLEDGED")

        msg_type = "Volume" if resource_type == "EBS" else "Instance"
        return jsonify({
            "text": f"{msg_type} {resource_id} acknowledged"
        }), 200

    elif action == "autofix":
        from storage.alert_state_manager import set_alert_state

        if resource_type == "EBS":
            from storage.ebs_remediation_manager import delete_volume_with_snapshot
            snapshot_id = delete_volume_with_snapshot(resource_id, account_id, account_name, region)
            if snapshot_id:
                set_alert_state(resource_id, "REMEDIATED")
                return jsonify({
                    "text": f"Resource optimized\nVolume: {resource_id}\nBackup Snapshot: {snapshot_id}\nAction: DELETE_VOLUME"
                }), 200
            else:
                return jsonify({
                    "text": f"Failed to optimize volume {resource_id} (or already remediated)"
                }), 500
        else:
            from storage.remediation_manager import stop_instance_with_backup
            ami_id = stop_instance_with_backup(resource_id, account_id, account_name, region)
            if ami_id:
                set_alert_state(resource_id, "REMEDIATED")
                return jsonify({
                    "text": f"Resource optimized\nInstance: {resource_id}\nBackup AMI: {ami_id}\nAction: STOP_INSTANCE"
                }), 200
            else:
                return jsonify({
                    "text": f"Failed to optimize resource {resource_id}"
                }), 500

    msg_type = "Volume" if resource_type == "EBS" else "Instance"
    return {
        "text": f"Action '{action}' recorded for {msg_type} {resource_id}"
    }


if __name__ == "__main__":
    app.run(port=5000)