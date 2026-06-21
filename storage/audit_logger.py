from datetime import datetime, timezone
import boto3
from scanner.config import AWS_REGION, AUDIT_TABLE

def log_action(instance_id, action, account_id="Unknown", account_name="Unknown", region="Unknown", skip_reason=None):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(AUDIT_TABLE)
        item = {
            "instance_id": instance_id,
            "timestamp": timestamp,
            "action": action,
            "account_id": account_id,
            "account_name": account_name,
            "region": region
        }
        if skip_reason:
            item["skip_reason"] = skip_reason
            
        table.put_item(Item=item)
    except Exception as e:
        print(f"Error logging action to DynamoDB: {e}")
