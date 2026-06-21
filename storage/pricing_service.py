import boto3
import json
from storage.pricing_cache import get_cached_price, set_cached_price

def get_region_location_name(region_code):
    mapping = {
        "us-east-1": "US East (N. Virginia)",
        "us-east-2": "US East (Ohio)",
        "us-west-1": "US West (N. California)",
        "us-west-2": "US West (Oregon)",
        "ap-south-1": "Asia Pacific (Mumbai)",
        "ap-northeast-1": "Asia Pacific (Tokyo)",
        "ap-northeast-2": "Asia Pacific (Seoul)",
        "ap-northeast-3": "Asia Pacific (Osaka)",
        "ap-southeast-1": "Asia Pacific (Singapore)",
        "ap-southeast-2": "Asia Pacific (Sydney)",
        "ap-southeast-3": "Asia Pacific (Jakarta)",
        "ap-southeast-4": "Asia Pacific (Melbourne)",
        "ca-central-1": "Canada (Central)",
        "eu-central-1": "Europe (Frankfurt)",
        "eu-west-1": "Europe (Ireland)",
        "eu-west-2": "Europe (London)",
        "eu-west-3": "Europe (Paris)",
        "eu-north-1": "Europe (Stockholm)",
        "eu-south-1": "Europe (Milan)",
        "me-south-1": "Middle East (Bahrain)",
        "sa-east-1": "South America (Sao Paulo)"
    }
    return mapping.get(region_code, "US East (N. Virginia)")

def get_ebs_monthly_cost(volume_type, size_gb, region="ap-south-1"):
    try:
        cache_key = f"ebs:{volume_type}:{region}"
        cached_price = get_cached_price(cache_key)
        if cached_price is not None:
            return cached_price * size_gb
            
        print("Fetching Pricing API data...")
        location = get_region_location_name(region)
        pricing = boto3.client("pricing", region_name="us-east-1")
        response = pricing.get_products(
            ServiceCode="AmazonEC2",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "volumeApiName", "Value": volume_type},
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Storage"}
            ]
        )
        
        price_list = response.get("PriceList", [])
        if not price_list:
            raise Exception("No pricing products found")
            
        product = json.loads(price_list[0])
        terms = product.get("terms", {}).get("OnDemand", {})
        for term_id, term_val in terms.items():
            price_dimensions = term_val.get("priceDimensions", {})
            for dim_id, dim_val in price_dimensions.items():
                unit_price = float(dim_val.get("pricePerUnit", {}).get("USD", 0.0))
                set_cached_price(cache_key, unit_price)
                return unit_price * size_gb
                
        raise Exception("Pricing dimensions not found in product terms")
    except Exception as e:
        print("Pricing API unavailable")
        print("Falling back to estimated savings")
        return 0.0

def get_ec2_monthly_cost(instance_type, region="ap-south-1"):
    try:
        cache_key = f"ec2:{instance_type}:{region}"
        cached_price = get_cached_price(cache_key)
        if cached_price is not None:
            return cached_price * 24 * 30
            
        print("Fetching Pricing API data...")
        location = get_region_location_name(region)
        pricing = boto3.client("pricing", region_name="us-east-1")
        response = pricing.get_products(
            ServiceCode="AmazonEC2",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
                {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"}
            ]
        )
        
        price_list = response.get("PriceList", [])
        if not price_list:
            raise Exception("No pricing products found")
            
        product = json.loads(price_list[0])
        terms = product.get("terms", {}).get("OnDemand", {})
        for term_id, term_val in terms.items():
            price_dimensions = term_val.get("priceDimensions", {})
            for dim_id, dim_val in price_dimensions.items():
                hourly_rate = float(dim_val.get("pricePerUnit", {}).get("USD", 0.0))
                set_cached_price(cache_key, hourly_rate)
                return hourly_rate * 24 * 30
                
        raise Exception("Pricing dimensions not found in product terms")
    except Exception as e:
        print("Pricing API unavailable")
        print("Falling back to estimated savings")
        return 0.0
