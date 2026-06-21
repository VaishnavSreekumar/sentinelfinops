import boto3
from datetime import datetime, timezone
from scanner.config import AWS_REGION, ACCOUNT_REGISTRY_TABLE

def discover_accounts():
    print("Discovering AWS accounts...")
    org = boto3.client("organizations")
    try:
        paginator = org.get_paginator("list_accounts")
        accounts = []
        for page in paginator.paginate():
            for acc in page.get("Accounts", []):
                # Ignore suspended and closed accounts
                if acc.get("Status") == "ACTIVE":
                    accounts.append({
                        "account_id": acc["Id"],
                        "account_name": acc["Name"],
                        "account_email": acc["Email"],
                        "account_status": acc["Status"]
                    })
        
        # Persist results in DynamoDB registry
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(ACCOUNT_REGISTRY_TABLE)
        last_seen = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        
        for acc in accounts:
            try:
                table.put_item(
                    Item={
                        "account_id": acc["account_id"],
                        "account_name": acc["account_name"],
                        "account_email": acc["account_email"],
                        "account_status": acc["account_status"],
                        "last_seen": last_seen
                    }
                )
            except Exception as ddb_err:
                print(f"Error persisting account {acc['account_id']} registry record: {ddb_err}")
                
        print(f"Accounts discovered: {len(accounts)}")
        return accounts
    except Exception as e:
        print(f"Error during account discovery: {e}")
        # Return empty list if Organizations API fails (e.g. not in Organization)
        return []
