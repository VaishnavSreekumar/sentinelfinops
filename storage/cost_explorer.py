import boto3
from datetime import datetime, timezone, timedelta
from scanner.config import AWS_REGION

def get_monthly_cost_for_resource(resource_id):
    print("Fetching Cost Explorer data...")
    try:
        # Cost Explorer client must query us-east-1 endpoint
        ce = boto3.client("ce", region_name="us-east-1")
        
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date_30 = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Try 30 days query first
        try:
            response = ce.get_cost_and_usage_with_resources(
                TimePeriod={
                    'Start': start_date_30,
                    'End': end_date
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                Filter={
                    'Dimensions': {
                        'Key': 'RESOURCE_ID',
                        'Values': [resource_id]
                    }
                }
            )
            total_cost = 0.0
            for result in response.get("ResultsByTime", []):
                amount = result.get("Total", {}).get("UnblendedCost", {}).get("Amount", "0")
                total_cost += float(amount)
                
            if total_cost > 0.0:
                print(f"Actual Monthly Cost: ${total_cost:.2f}")
                return total_cost
        except Exception:
            pass

        # Fallback to last 14 days query due to AWS RESOURCE_ID 14-day limit
        start_date_14 = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
        response = ce.get_cost_and_usage_with_resources(
            TimePeriod={
                'Start': start_date_14,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            Filter={
                'Dimensions': {
                    'Key': 'RESOURCE_ID',
                    'Values': [resource_id]
                }
            }
        )
        
        total_cost = 0.0
        for result in response.get("ResultsByTime", []):
            amount = result.get("Total", {}).get("UnblendedCost", {}).get("Amount", "0")
            total_cost += float(amount)
            
        scaled_cost = total_cost * (30.0 / 14.0)
        if scaled_cost > 0.0:
            print(f"Actual Monthly Cost: ${scaled_cost:.2f}")
            return scaled_cost
            
        print("Cost Explorer resource data unavailable")
        print("Falling back to estimated savings")
        print("Actual Monthly Cost: $0.00")
        return 0.0

    except Exception as e:
        print("Cost Explorer resource data unavailable")
        print("Falling back to estimated savings")
        print("Actual Monthly Cost: $0.00")
        return 0.0
