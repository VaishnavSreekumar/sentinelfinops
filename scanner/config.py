import os

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
SNOOZE_TABLE = "sentinelfinops-snoozes"
AUDIT_TABLE = "sentinelfinops-audit"
ALERT_STATE_TABLE = "sentinelfinops-alert-state"
REMEDIATION_TABLE = "sentinelfinops-remediation-history"
SAVINGS_HISTORY_TABLE = "sentinelfinops-savings-history"
PRICING_CACHE_TABLE = "sentinelfinops-pricing-cache"

ACCOUNT_REGISTRY_TABLE = "sentinelfinops-account-registry"
REMEDIATION_LOCKS_TABLE = "sentinelfinops-remediation-locks"

ALLOWED_REGIONS = [r.strip() for r in os.getenv("ALLOWED_REGIONS", "").split(",") if r.strip()]
DENIED_REGIONS = [r.strip() for r in os.getenv("DENIED_REGIONS", "").split(",") if r.strip()]
DRY_RUN = os.getenv("DRY_RUN", "False").lower() in ("true", "1", "yes")

MAINTENANCE_WINDOW_START = os.getenv("MAINTENANCE_WINDOW_START")  # e.g., "02:00"
MAINTENANCE_WINDOW_END = os.getenv("MAINTENANCE_WINDOW_END")      # e.g., "05:00"



