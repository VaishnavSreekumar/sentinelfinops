import sys
import os
from dotenv import load_dotenv

# Load environment overrides from local files
load_dotenv(".env", override=True)
load_dotenv(".ENV", override=True)

# Check for global --dry-run CLI flag and set environment override before importing config
if "--dry-run" in sys.argv:
    os.environ["DRY_RUN"] = "True"
    sys.argv.remove("--dry-run")

from version import VERSION
from scanner.run_scan import run_scan
from reporting.savings_report import (
    generate_savings_report, generate_trend_report,
    generate_monthly_report, generate_account_report
)
from validation.install_validator import validate_installation
from monitoring.healthcheck import health_check
from bootstrap.bootstrap_accounts import bootstrap_all_accounts
from notifications.notifier import send_alert

def print_locks_table():
    import boto3
    from datetime import datetime, timezone
    from scanner.config import AWS_REGION, REMEDIATION_LOCKS_TABLE
    
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(REMEDIATION_LOCKS_TABLE)
    
    try:
        response = table.scan()
        items = response.get("Items", [])
        
        if not items:
            print("No active or expired locks found in the database.")
            return
            
        header_fmt = "{:<18} | {:<5} | {:<15} | {:<16} | {:<16} | {:<10} | {:<10} | {:<8} | {:<20}"
        print(header_fmt.format(
            "RESOURCE", "TYPE", "OWNER", "EXECUTION ID", "REQUEST ID", "AGE", "TTL", "STATUS", "LAST HEARTBEAT"
        ))
        print("-" * 140)
        
        now = datetime.now(timezone.utc)
        
        for item in items:
            res_id = item.get("resource_id", "Unknown")
            res_type = item.get("resource_type", "EC2")
            owner = item.get("lock_owner", "Unknown")
            exec_id = item.get("execution_id", "Unknown")
            if len(exec_id) > 13:
                exec_id = exec_id[:13] + "..."
            req_id = item.get("request_id", "Unknown")
            if len(req_id) > 13:
                req_id = req_id[:13] + "..."
                
            locked_at_str = item.get("locked_at", "")
            expires_at_str = item.get("expires_at", "")
            
            age_str = "Unknown"
            ttl_str = "Unknown"
            status = "FREE"
            
            if locked_at_str:
                try:
                    locked_at = datetime.fromisoformat(locked_at_str.replace("Z", "+00:00"))
                    age_delta = now - locked_at
                    seconds = int(age_delta.total_seconds())
                    if seconds < 0:
                        seconds = 0
                    mins, secs = divmod(seconds, 60)
                    age_str = f"{mins}m {secs}s"
                except Exception:
                    pass
                    
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                    if now < expires_at:
                         status = "ACTIVE"
                         time_left = expires_at - now
                         seconds = int(time_left.total_seconds())
                         mins, secs = divmod(seconds, 60)
                         ttl_str = f"{mins}m {secs}s"
                    else:
                         status = "EXPIRED"
                         ttl_str = "Expired"
                except Exception:
                    pass
                    
            print(header_fmt.format(
                res_id, res_type, owner, exec_id, req_id, age_str, ttl_str, status, locked_at_str
            ))
            
    except Exception as e:
        print(f"Failed to retrieve locks from DynamoDB: {e}")

def print_help():
    print(f"SentinelFinOps Engine CLI v{VERSION}")
    print("Usage: python main.py [command] [options]")
    print("\nCommands:")
    print("  scan          Run optimization scans (default command)")
    print("  validate      Run enterprise installation validation")
    print("  health        Run connectivity and database healthchecks")
    print("  locks         Show active and expired remediation locks")
    print("  bootstrap     Bootstrap Organizations member accounts (creates SentinelFinOpsExecutionRole)")
    print("  test-slack    Send an explicit Slack notification test")
    print("  report        Generate cost savings report")
    print("  trends        Generate trend analysis report")
    print("  monthly       Generate monthly aggregation report")
    print("  accounts      Generate cross-account breakdown report")
    print("  version       Print platform version")
    print("\nOptions:")
    print("  --dry-run     Enable dry-run mode, overriding configuration settings")

def run_test_slack():
    print("Sending Slack test notification...")
    try:
        send_alert(
            instance_name="SentinelFinOps-Test-Instance",
            instance_id="i-099999999999abcde",
            owner="FinOps-Verification",
            cpu_usage=0.85,
            monthly_cost=120.00,
            account_id="123456789012",
            account_name="SentinelFinOps-Staging",
            region="ap-south-1"
        )
        print("Slack test notification execution completed. Check your Slack channel.")
    except Exception as e:
        print(f"Failed to send Slack test notification: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "version":
            print(f"SentinelFinOps Platform v{VERSION}")
        elif arg == "validate":
            validate_installation()
        elif arg == "health":
            health_check()
        elif arg == "locks":
            print_locks_table()
        elif arg == "bootstrap":
            bootstrap_all_accounts()
        elif arg == "test-slack":
            run_test_slack()
        elif arg == "report":
            generate_savings_report()
        elif arg == "trends":
            generate_trend_report()
        elif arg == "monthly":
            generate_monthly_report()
        elif arg == "accounts":
            generate_account_report()
        elif arg == "scan":
            run_scan()
        elif arg in ("-h", "--help", "help"):
            print_help()
        else:
            print(f"Unknown command: {arg}")
            print_help()
            sys.exit(1)
    else:
        run_scan()
