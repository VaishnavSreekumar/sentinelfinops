from datetime import datetime, timezone
from decimal import Decimal
import boto3
from scanner.config import AWS_REGION, PRICING_CACHE_TABLE

def get_cached_price(cache_key):
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(PRICING_CACHE_TABLE)
        response = table.get_item(Key={"cache_key": cache_key})
        item = response.get("Item")
        if item:
            return float(item.get("price", 0.0))
        return None
    except Exception as e:
        print(f"Error checking pricing cache: {e}")
        return None

def set_cached_price(cache_key, price):
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(PRICING_CACHE_TABLE)
        updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        table.put_item(
            Item={
                "cache_key": cache_key,
                "price": Decimal(str(price)),
                "updated_at": updated_at
            }
        )
    except Exception as e:
        print(f"Error writing to pricing cache: {e}")
