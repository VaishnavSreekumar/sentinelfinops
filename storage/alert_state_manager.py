from datetime import datetime, timezone
import boto3
from scanner.config import AWS_REGION, ALERT_STATE_TABLE

def get_alert_state(instance_id):
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(ALERT_STATE_TABLE)
        response = table.get_item(Key={"instance_id": instance_id})
        item = response.get("Item")
        if item:
            return item.get("state", "NEW")
        return "NEW"
    except Exception as e:
        print(f"Error getting alert state: {e}")
        return "NEW"

def set_alert_state(instance_id, state):
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(ALERT_STATE_TABLE)
        updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        table.put_item(
            Item={
                "instance_id": instance_id,
                "state": state,
                "updated_at": updated_at
            }
        )
    except Exception as e:
        print(f"Error setting alert state: {e}")

def clear_alert_state(instance_id):
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(ALERT_STATE_TABLE)
        table.delete_item(Key={"instance_id": instance_id})
    except Exception as e:
        print(f"Error clearing alert state: {e}")
