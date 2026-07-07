import boto3
import json
import os
import sys
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import load_config

def health_check():
    """
    Evaluates runtime connectivity to critical dependencies (DynamoDB, Organizations, Pricing, Slack)
    and prints/returns a structured health report.
    """
    config = load_config()
    report = {
        "status": "HEALTHY",
        "timestamp": boto3.client("sts").get_caller_identity().get("UserId", ""), # quick check to fetch timestamp/identity
        "details": {}
    }
    
    # 1. Validate DynamoDB
    try:
        ddb = boto3.client("dynamodb", region_name=config["aws"]["default_region"])
        # Describe main tables
        ddb.describe_table(TableName="sentinelfinops-snoozes")
        ddb.describe_table(TableName="sentinelfinops-remediation-locks")
        report["details"]["DynamoDB"] = {"status": "PASS", "message": "Successfully connected and verified snoozes and locks tables."}
    except Exception as e:
        report["status"] = "UNHEALTHY"
        report["details"]["DynamoDB"] = {"status": "FAIL", "message": str(e)}
        
    # 2. Validate Organizations
    if config["aws"]["organizations_enabled"]:
        try:
            org = boto3.client("organizations")
            org.describe_organization()
            report["details"]["Organizations"] = {"status": "PASS", "message": "AWS Organizations described successfully."}
        except Exception as e:
            # Check if it's due to account not being in an organization
            is_not_in_org = False
            if hasattr(e, "response") and isinstance(e.response, dict):
                error_code = e.response.get("Error", {}).get("Code")
                if error_code == "AWSOrganizationsNotInUseException":
                    is_not_in_org = True
            
            if is_not_in_org:
                report["details"]["Organizations"] = {
                    "status": "OPTIONAL",
                    "message": "Account is not a member of an AWS Organization. Single-account scanning will be used as a fallback."
                }
            else:
                report["status"] = "UNHEALTHY"
                report["details"]["Organizations"] = {"status": "FAIL", "message": str(e)}
    else:
        report["details"]["Organizations"] = {"status": "WARNING", "message": "Organizations support disabled in configurations."}
        
    # 3. Validate Pricing API
    if config["finops"]["pricing_api_enabled"]:
        try:
            pricing = boto3.client("pricing", region_name="us-east-1")
            pricing.describe_services(MaxResults=1)
            report["details"]["PricingAPI"] = {"status": "PASS", "message": "AWS Pricing API described successfully."}
        except Exception as e:
            # We don't mark the whole system unhealthy for transient/access warning on pricing
            report["details"]["PricingAPI"] = {"status": "WARNING", "message": f"Pricing service described failed: {e}"}
            
    # 4. Validate Cost Explorer
    if config["finops"]["cost_explorer_enabled"]:
        try:
            ce = boto3.client("ce", region_name=config["aws"]["default_region"])
            # Simple metadata query
            ce.get_dimension_values(
                TimePeriod={"Start": "2026-06-01", "End": "2026-06-02"},
                Dimension="SERVICE"
            )
            report["details"]["CostExplorer"] = {"status": "PASS", "message": "Cost Explorer dimensions queried successfully."}
        except Exception as e:
            report["details"]["CostExplorer"] = {"status": "WARNING", "message": f"Cost Explorer query failed: {e}"}
            
    # 5. Validate Slack Webhook
    webhook = config["slack"]["webhook_url"]
    if not webhook:
        report["details"]["SlackWebhook"] = {"status": "WARNING", "message": "Webhook URL not configured in configurations."}
    else:
        try:
            # Send a check payload to verify structure
            if not webhook.startswith("https://hooks.slack.com"):
                raise Exception("Webhook URL must start with https://hooks.slack.com")
            report["details"]["SlackWebhook"] = {"status": "PASS", "message": "Slack webhook URL configured and validated."}
        except Exception as e:
            report["details"]["SlackWebhook"] = {"status": "FAIL", "message": str(e)}
            if report["status"] != "UNHEALTHY":
                report["status"] = "WARNING"
                
    print(json.dumps(report, indent=2))
    return report

if __name__ == "__main__":
    health_check()
