import sys
import os

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

def print_help():
    print(f"SentinelFinOps Engine CLI v{VERSION}")
    print("Usage: python main.py [command] [options]")
    print("\nCommands:")
    print("  scan          Run optimization scans (default command)")
    print("  validate      Run enterprise installation validation")
    print("  health        Run connectivity and database healthchecks")
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
