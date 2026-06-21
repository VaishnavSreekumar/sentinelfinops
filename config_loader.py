import os
import yaml

def load_config(config_path=None):
    """
    Load configurations from config/settings.yaml using PyYAML safe_load.
    Supports environment variable overrides for 12-factor production deployments.
    Validates that config_version is exactly 1.
    """
    if not config_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config", "settings.yaml")
        
    if not os.path.exists(config_path):
        # Fallback to current working directory
        config_path = os.path.join(os.getcwd(), "config", "settings.yaml")
        
    if not os.path.exists(config_path):
        # Return empty dictionary with config_version 1 to fall back to validation defaults
        config = {"config_version": 1}
    else:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            # Fallback or propagate parsing error
            raise ValueError(f"Error parsing YAML config at {config_path}: {e}")
            
        if not config or "config_version" not in config:
            raise ValueError(f"Configuration file at {config_path} is missing 'config_version'.")
            
        if config["config_version"] != 1:
            raise ValueError(f"Unsupported config_version: {config['config_version']}. Supported version is 1.")
            
    return validate_and_apply_defaults(config)

def validate_and_apply_defaults(config):
    """
    Applies default values to missing keys and merges environment variable overrides.
    """
    for sec in ["aws", "slack", "remediation", "finops", "reporting"]:
        if sec not in config:
            config[sec] = {}
            
    aws = config["aws"]
    slack = config["slack"]
    remediation = config["remediation"]
    finops = config["finops"]
    reporting = config["reporting"]
    
    # Apply AWS defaults
    aws["default_region"] = aws.get("default_region", "ap-south-1")
    aws["organizations_enabled"] = aws.get("organizations_enabled", True)
    aws["management_account_id"] = aws.get("management_account_id", "867344453130")
    aws["role_name"] = aws.get("role_name", "SentinelFinOpsExecutionRole")
    aws["allowed_regions"] = aws.get("allowed_regions", [])
    aws["denied_regions"] = aws.get("denied_regions", [])
    
    # Apply Slack defaults
    slack["webhook_url"] = slack.get("webhook_url", None)
    slack["notification_channel"] = slack.get("notification_channel", "#general")
    
    # Apply Remediation defaults
    remediation["dry_run"] = remediation.get("dry_run", False)
    remediation["backup_enabled"] = remediation.get("backup_enabled", True)
    remediation["remediation_lock_timeout_minutes"] = int(remediation.get("remediation_lock_timeout_minutes", 15))
    
    # Apply FinOps thresholds
    finops["cpu_threshold"] = float(finops.get("cpu_threshold", 5.0))
    finops["idle_days_threshold"] = int(finops.get("idle_days_threshold", 7))
    finops["cost_explorer_enabled"] = finops.get("cost_explorer_enabled", True)
    finops["pricing_api_enabled"] = finops.get("pricing_api_enabled", True)
    
    # Apply Reporting defaults
    reporting["report_retention_days"] = int(reporting.get("report_retention_days", 90))
    reporting["trend_history_days"] = int(reporting.get("trend_history_days", 30))
    
    # Environment variable overrides
    if os.getenv("SLACK_WEBHOOK_URL"):
        slack["webhook_url"] = os.getenv("SLACK_WEBHOOK_URL")
    if os.getenv("AWS_REGION"):
        aws["default_region"] = os.getenv("AWS_REGION")
    if os.getenv("DRY_RUN"):
        remediation["dry_run"] = os.getenv("DRY_RUN").lower() in ("true", "1", "yes")
    if os.getenv("MAINTENANCE_WINDOW_START"):
        config["remediation_window_start"] = os.getenv("MAINTENANCE_WINDOW_START")
    if os.getenv("MAINTENANCE_WINDOW_END"):
        config["remediation_window_end"] = os.getenv("MAINTENANCE_WINDOW_END")
        
    return config
