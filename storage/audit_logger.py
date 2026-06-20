from datetime import datetime, timezone
import boto3
from scanner.config import AWS_REGION, AUDIT_TABLE

def log_action(instance_id, action):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(AUDIT_TABLE)
        table.put_item(
            Item={
                "instance_id": instance_id,
                "timestamp": timestamp,
                "action": action
            }
        )
    except Exception as e:
        print(f"Error logging action to DynamoDB: {e}")
