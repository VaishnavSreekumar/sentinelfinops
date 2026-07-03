import boto3
import urllib.request
import urllib.error
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import load_config
from version import VERSION

def validate_installation():
    config = load_config()
    print("=" * 65)
    print(f"Starting SentinelFinOps Enterprise Installation Validation (v{VERSION})...")
    print("=" * 65)
    
    passes = 0
    warnings = 0
    fails = 0
    
    region = config["aws"]["default_region"]
    role_name = config["aws"]["role_name"]
    
    def log_result(status, check_name, message):
        nonlocal passes, warnings, fails
        print(f"[{status}] {check_name}: {message}")
        if status == "PASS":
            passes += 1
        elif status == "WARNING":
            warnings += 1
        elif status == "FAIL":
            fails += 1

    # 1. Check Caller Identity & STS
    sts_client = None
    identity = None
    try:
        sts_client = boto3.client("sts", region_name=region)
        identity = sts_client.get_caller_identity()
        log_result("PASS", "STS Connection / Identity", f"Caller Account={identity.get('Account')}, ARN={identity.get('Arn')}")
    except Exception as e:
        log_result("FAIL", "STS Connection / Identity", f"Failed to get caller identity: {e}")
        # If STS fails, we cannot proceed with most AWS queries safely
        print("Aborting validation: STS credentials not functional.")
        return "FAIL"

    # 2. Check IAM Permissions Simulation
    try:
        iam = boto3.client("iam", region_name=region)
        caller_arn = identity.get("Arn", "")
        
        # If caller is an IAM role or user, we can simulate policy.
        # For federated sessions (assumed-role), we simulate using the base role ARN.
        policy_source_arn = caller_arn
        if ":assumed-role/" in caller_arn:
            parts = caller_arn.split("/")
            role_name_part = parts[1]
            account_id = caller_arn.split(":")[4]
            policy_source_arn = f"arn:aws:iam::{account_id}:role/{role_name_part}"
        
        sim_actions = [
            "dynamodb:GetItem",
            "dynamodb:PutItem",
            "cloudwatch:PutMetricData",
            "sts:AssumeRole"
        ]
        if config["aws"]["organizations_enabled"]:
            sim_actions.append("organizations:ListAccounts")
            
        sim_response = iam.simulate_principal_policy(
            PolicySourceArn=policy_source_arn,
            ActionNames=sim_actions
        )
        
        failed_sims = []
        for eval_result in sim_response.get("EvaluationResults", []):
            if eval_result.get("EvalDecision") != "allowed":
                failed_sims.append(eval_result.get("EvalActionName"))
                
        if failed_sims:
            log_result("WARNING", "IAM Policy Simulation", f"Actions not explicitly allowed: {', '.join(failed_sims)}")
        else:
            log_result("PASS", "IAM Policy Simulation", "All required core actions (DynamoDB, CloudWatch, STS, Organizations) are allowed.")
    except Exception as e:
        log_result("WARNING", "IAM Policy Simulation", f"Unable to simulate principal policy: {e} (Using direct action fallback checks)")

    # 3. Check Organizations API Access
    if config["aws"]["organizations_enabled"]:
        try:
            org = boto3.client("organizations", region_name=region)
            org.describe_organization()
            log_result("PASS", "AWS Organizations Permissions", "DescribeOrganization call succeeded.")
        except Exception as e:
            log_result("FAIL", "AWS Organizations Permissions", f"DescribeOrganization call failed: {e}")
    else:
        log_result("WARNING", "AWS Organizations Permissions", "Organizations integration disabled in configuration settings.")

    # 4. Check Pricing API Access
    if config["finops"]["pricing_api_enabled"]:
        try:
            pricing = boto3.client("pricing", region_name="us-east-1")
            pricing.describe_services(MaxResults=1)
            log_result("PASS", "AWS Pricing API Permissions", "DescribeServices connection validated.")
        except Exception as e:
            log_result("WARNING", "AWS Pricing API Permissions", f"DescribeServices failed (check pricing region/SCP/IAM): {e}")
    else:
        log_result("WARNING", "AWS Pricing API Permissions", "Pricing API disabled in configuration settings.")

    # 5. Check Cost Explorer Access
    if config["finops"]["cost_explorer_enabled"]:
        try:
            ce = boto3.client("ce", region_name=region)
            ce.get_dimension_values(
                TimePeriod={"Start": "2026-06-01", "End": "2026-06-02"},
                Dimension="SERVICE"
            )
            log_result("PASS", "AWS Cost Explorer Permissions", "GetDimensionValues query succeeded.")
        except Exception as e:
            log_result("WARNING", "AWS Cost Explorer Permissions", f"Query failed (check Cost Explorer activation/IAM): {e}")
    else:
        log_result("WARNING", "AWS Cost Explorer Permissions", "Cost Explorer disabled in configuration settings.")

    # 6. Check DynamoDB Tables
    tables = [
        "sentinelfinops-snoozes",
        "sentinelfinops-audit",
        "sentinelfinops-alert-state",
        "sentinelfinops-remediation-history",
        "sentinelfinops-savings-history",
        "sentinelfinops-pricing-cache",
        "sentinelfinops-account-registry",
        "sentinelfinops-remediation-locks"
    ]
    try:
        ddb = boto3.client("dynamodb", region_name=region)
        for table in tables:
            try:
                desc = ddb.describe_table(TableName=table)
                status = desc["Table"]["TableStatus"]
                if status == "ACTIVE":
                    log_result("PASS", f"DynamoDB Table: {table}", "ACTIVE")
                else:
                    log_result("WARNING", f"DynamoDB Table: {table}", f"Status is {status}")
            except Exception as e:
                log_result("FAIL", f"DynamoDB Table: {table}", f"Describe failed: {e}")
    except Exception as e:
        log_result("FAIL", "DynamoDB Client", f"Failed to build DynamoDB client: {e}")

    # 6b. Check Lock Timeout Configuration
    try:
        lock_timeout = config["remediation"].get("remediation_lock_timeout_minutes")
        if lock_timeout is not None and isinstance(lock_timeout, int) and lock_timeout > 0:
            log_result("PASS", "Lock Timeout Configuration", f"Configured timeout: {lock_timeout} minutes")
        else:
            log_result("FAIL", "Lock Timeout Configuration", f"Invalid lock timeout: {lock_timeout}")
    except Exception as e:
        log_result("FAIL", "Lock Timeout Configuration", f"Error checking configuration: {e}")

    # 6c. Check Locks Table Conditional Writes Capability
    try:
        from storage.remediation_lock import acquire_lock, release_lock
        import uuid
        
        test_res_id = f"sentinelfinops-validator-test-lock-{uuid.uuid4()}"
        test_exec_id = str(uuid.uuid4())
        
        res_a = acquire_lock(
            resource_id=test_res_id,
            execution_id=test_exec_id,
            resource_type="EC2",
            account_id="123456789012",
            region=region,
            lock_owner="Validator-Test"
        )
        
        if res_a.status == "ACQUIRED":
            dup_exec_id = str(uuid.uuid4())
            res_b = acquire_lock(
                resource_id=test_res_id,
                execution_id=dup_exec_id,
                resource_type="EC2",
                account_id="123456789012",
                region=region,
                lock_owner="Validator-Dup"
            )
            
            if res_b.status == "DENIED":
                res_c = release_lock(test_res_id, test_exec_id)
                if res_c.status == "RELEASED":
                    log_result("PASS", "Distributed Locks Functional Verification", "Verified lock acquisition, concurrency check (DENIED), and release.")
                else:
                    log_result("FAIL", "Distributed Locks Functional Verification", f"Release failed with status: {res_c.status}")
            else:
                release_lock(test_res_id, test_exec_id)
                log_result("FAIL", "Distributed Locks Functional Verification", f"Concurrency check failed: Duplicate lock acquisition returned status: {res_b.status}")
        else:
            log_result("FAIL", "Distributed Locks Functional Verification", f"Initial acquisition failed with status: {res_a.status}")
            
    except Exception as e:
        log_result("FAIL", "Distributed Locks Functional Verification", f"Error verifying locks behavior: {e}")

    # 7. Check Deployed Lambda Function & Environment Variables
    lambda_func_name = "sentinelfinops-scanner"
    try:
        lambda_client = boto3.client("lambda", region_name=region)
        func = lambda_client.get_function(FunctionName=lambda_func_name)
        log_result("PASS", f"Lambda Function: {lambda_func_name}", "Exists on AWS.")
        
        # Check environment variables
        env_vars = func.get("Configuration", {}).get("Environment", {}).get("Variables", {})
        required_vars = ["SLACK_WEBHOOK_URL"]
        missing_vars = [v for v in required_vars if v not in env_vars]
        if missing_vars:
            log_result("FAIL", f"Lambda: {lambda_func_name} Environment", f"Missing required environment variables on deployed function: {', '.join(missing_vars)}")
        else:
            optional_vars = ["SETTINGS_PATH"]
            found_optionals = [v for v in optional_vars if v in env_vars]
            msg = "All essential environment variables are set on deployed function."
            if found_optionals:
                msg += f" (Optional found: {', '.join(found_optionals)})"
            log_result("PASS", f"Lambda: {lambda_func_name} Environment", msg)
    except Exception as e:
        log_result("FAIL", f"Lambda Function: {lambda_func_name}", f"Failed to retrieve function: {e}")

    # 8. Check EventBridge Schedule Rule
    eb_rule_name = "sentinelfinops-hourly-schedule"
    try:
        ev = boto3.client("events", region_name=region)
        rule = ev.describe_rule(Name=eb_rule_name)
        rule_state = rule.get("State", "UNKNOWN")
        if rule_state == "ENABLED":
            log_result("PASS", f"EventBridge Rule: {eb_rule_name}", f"ENABLED (Schedule: {rule.get('ScheduleExpression')})")
        else:
            log_result("WARNING", f"EventBridge Rule: {eb_rule_name}", f"State is {rule_state}")
    except Exception as e:
        log_result("WARNING", f"EventBridge Rule: {eb_rule_name}", f"Not found or describe failed: {e}")

    # 9. Check Execution Role
    try:
        iam = boto3.client("iam", region_name=region)
        iam.get_role(RoleName=role_name)
        log_result("PASS", f"Execution Role: {role_name}", "Exists in local account.")
    except Exception as e:
        log_result("WARNING", f"Execution Role: {role_name}", f"Not found in local account: {e} (Might use direct organization cross-account assumption)")

    # 10. Check Slack Webhook Reachability (Non-pinging check to hooks.slack.com)
    webhook = config["slack"]["webhook_url"]
    if not webhook:
        log_result("WARNING", "Slack Webhook Configuration", "Webhook URL is missing.")
    elif not webhook.startswith("https://hooks.slack.com"):
        log_result("FAIL", "Slack Webhook Configuration", "Webhook URL does not start with https://hooks.slack.com")
    else:
        log_result("PASS", "Slack Webhook Configuration", "Webhook URL format is valid.")
        try:
            req = urllib.request.Request("https://hooks.slack.com", method="HEAD")
            with urllib.request.urlopen(req, timeout=5) as response:
                pass
            log_result("PASS", "Slack Egress/DNS Connectivity", "hooks.slack.com is reachable via HTTPS.")
        except Exception as e:
            log_result("WARNING", "Slack Egress/DNS Connectivity", f"Failed to establish HTTPS connection to hooks.slack.com: {e}")

    print("=" * 65)
    print("VALIDATION SUMMARY")
    print(f"PASS: {passes} | WARNING: {warnings} | FAIL: {fails}")
    print("=" * 65)
    
    if fails > 0:
        return "FAIL"
    elif warnings > 0:
        return "WARNING"
    return "PASS"

if __name__ == "__main__":
    validate_installation()
