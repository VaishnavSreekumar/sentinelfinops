import os
import sys

# Ensure root directory is in sys.path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from config_loader import load_config

_config = load_config()

AWS_REGION = _config["aws"]["default_region"]
SNOOZE_TABLE = "sentinelfinops-snoozes"
AUDIT_TABLE = "sentinelfinops-audit"
ALERT_STATE_TABLE = "sentinelfinops-alert-state"
REMEDIATION_TABLE = "sentinelfinops-remediation-history"
SAVINGS_HISTORY_TABLE = "sentinelfinops-savings-history"
PRICING_CACHE_TABLE = "sentinelfinops-pricing-cache"

ACCOUNT_REGISTRY_TABLE = "sentinelfinops-account-registry"
REMEDIATION_LOCKS_TABLE = "sentinelfinops-remediation-locks"

ALLOWED_REGIONS = _config["aws"]["allowed_regions"]
DENIED_REGIONS = _config["aws"]["denied_regions"]
DRY_RUN = _config["remediation"]["dry_run"]

MAINTENANCE_WINDOW_START = _config.get("remediation_window_start")
MAINTENANCE_WINDOW_END = _config.get("remediation_window_end")

SLACK_WEBHOOK_URL = _config["slack"]["webhook_url"]
SLACK_NOTIFICATION_CHANNEL = _config["slack"]["notification_channel"]
CPU_THRESHOLD = _config["finops"]["cpu_threshold"]
IDLE_DAYS_THRESHOLD = _config["finops"]["idle_days_threshold"]
COST_EXPLORER_ENABLED = _config["finops"]["cost_explorer_enabled"]
PRICING_API_ENABLED = _config["finops"]["pricing_api_enabled"]
ORGANIZATIONS_ENABLED = _config["aws"]["organizations_enabled"]
ROLE_NAME = _config["aws"]["role_name"]
MANAGEMENT_ACCOUNT_ID = _config["aws"]["management_account_id"]




