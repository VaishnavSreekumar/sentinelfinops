from datetime import datetime, timezone
import boto3
from scanner.config import AWS_REGION, SNOOZE_TABLE

def is_snoozed(instance_id):
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(SNOOZE_TABLE)
        response = table.get_item(Key={"instance_id": instance_id})
        item = response.get("Item")
        if not item:
            return False
        
        expiry_str = item.get("expiry_timestamp")
        if not expiry_str:
            return False
            
        expiry = datetime.fromisoformat(expiry_str)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
            
        current_time = datetime.now(timezone.utc)
        if current_time > expiry:
            return False
        return True
    except Exception:
        return False
