import os

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
SNOOZE_TABLE = "sentinelfinops-snoozes"
AUDIT_TABLE = "sentinelfinops-audit"
ALERT_STATE_TABLE = "sentinelfinops-alert-state"
REMEDIATION_TABLE = "sentinelfinops-remediation-history"
SAVINGS_HISTORY_TABLE = "sentinelfinops-savings-history"
PRICING_CACHE_TABLE = "sentinelfinops-pricing-cache"


