import os

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
SNOOZE_TABLE = "sentinelfinops-snoozes"
AUDIT_TABLE = "sentinelfinops-audit"
ALERT_STATE_TABLE = "sentinelfinops-alert-state"
REMEDIATION_TABLE = "sentinelfinops-remediation-history"

