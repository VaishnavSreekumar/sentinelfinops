"""
Production Environment Safeguard Rule.
Blocks low confidence actions, production assets, unowned resources, and destructive changes without backups.
"""
from typing import Any, List, Union
from policy.rules.base_rule import PolicyRule
from ai.contracts.enums import RecommendedAction

class ProductionGuardRule(PolicyRule):
    """
    Asserts safety boundaries for automated remediation on AWS resources.
    Enforces rules on:
      1. AI model confidence score threshold (configurable, default 0.90).
      2. Environment validation (blocks 'production' or 'prod', permits dev/test/sandbox/personal/lab/training).
      3. Critical resource naming patterns (blocks 'prod', 'critical', 'database', etc.).
      4. Missing owner or attribution metadata.
      5. Structured backup checks (snapshot/AMI) for destructive actions (e.g. risk_assessment.backup_verified == True).
    """
    name = "ProductionGuardRule"

    def __init__(self, config: Any = None):
        self.config = config or {}

    def evaluate(self, recommendation, context: Any = None) -> Union[bool, List[str]]:
        """
        Validates the recommendation against the target rules criteria.
        Returns a list of violation strings if any rule fails, or True if passed.
        """
        violations: List[str] = []

        # 1. Fail Closed if context is missing
        if context is None:
            return ["[Blocked] ProductionGuardRule: Condition 'ContextVerification' triggered (context payload is missing). Recommended operator action: Manual intervention required."]

        # 2. Extract tags for inspection
        tags = {}
        raw_res = getattr(context, "raw_resource", {}) or {}
        tags_list = raw_res.get("tags") or []
        
        if isinstance(tags_list, list):
            for t in tags_list:
                key = t.get("Key")
                val = t.get("Value")
                if key:
                    tags[key.lower().strip()] = (val or "").strip()
        elif isinstance(tags_list, dict):
            tags = {k.lower().strip(): (v or "").strip() for k, v in tags_list.items()}

        # 3. Model Confidence Check
        confidence = getattr(recommendation, "confidence_score", 0.0)
        # Resolve threshold from configuration settings
        min_confidence = 0.90
        if isinstance(self.config, dict):
            min_confidence = self.config.get("ai", {}).get("min_confidence_threshold", 0.90)
            
        if confidence < min_confidence:
            violations.append(
                f"[Blocked] ProductionGuardRule: Condition 'ConfidenceScore' triggered (AI confidence score {confidence} is below minimum threshold of {min_confidence}). "
                f"Recommended operator action: Review resource utilization manually."
            )

        # 4. Environment Check
        env = (tags.get("environment") or tags.get("env") or "").lower().strip()
        allowed_envs = ["development", "dev", "testing", "test", "sandbox", "lab", "personal", "training"]
        
        account_name = (getattr(context, "account_name", "") or "").lower()
        is_prod_account = any(p in account_name for p in ["prod", "production"])

        if not env:
            if is_prod_account:
                violations.append(
                    "[Blocked] ProductionGuardRule: Condition 'EnvironmentIsolation' triggered (resource resides in Production account but lacks environment tag). "
                    "Recommended operator action: Manual validation required."
                )
            else:
                violations.append(
                    "[Blocked] ProductionGuardRule: Condition 'EnvironmentIsolation' triggered (environment tag is missing). "
                    "Recommended operator action: Add Environment metadata tag to permit remediation."
                )
        elif any(p in env for p in ["prod", "production"]) or is_prod_account:
            violations.append(
                f"[Blocked] ProductionGuardRule: Condition 'EnvironmentIsolation' triggered (Production environment detected: '{env}'). "
                f"Recommended operator action: Production resources must be remediated manually."
            )
        elif not any(ae in env for ae in allowed_envs):
            violations.append(
                f"[Blocked] ProductionGuardRule: Condition 'EnvironmentIsolation' triggered (environment '{env}' is not allowed for auto-remediation). "
                f"Recommended operator action: Verify environment configuration settings."
            )

        # 5. Critical Naming Check
        name = (tags.get("name") or raw_res.get("instance_name") or raw_res.get("volume_id") or "").lower().strip()
        critical_keywords = ["prod", "production", "critical", "database", "db", "payment", "identity", "auth"]
        for keyword in critical_keywords:
            if keyword in name:
                violations.append(
                    f"[Blocked] ProductionGuardRule: Condition 'CriticalNaming' triggered (resource name contains sensitive keyword '{keyword}'). "
                    f"Recommended operator action: Critical databases and assets require manual operations."
                )
                break

        # 6. Missing Owner attribution check
        owner_found = False
        owner_info = getattr(context, "owner_info", None)
        if owner_info:
            if owner_info.owner_arn or owner_info.team or owner_info.email or owner_info.cloudtrail_actor:
                owner_found = True
        
        if not owner_found:
            if tags.get("owner") or tags.get("contact"):
                owner_found = True

        if not owner_found:
            violations.append(
                "[Blocked] ProductionGuardRule: Condition 'OwnerVerification' triggered (no owner or contact details could be resolved). "
                "Recommended operator action: Set Owner or Contact metadata tag."
            )

        # 7. Structured Backup Check (must verify backup intent via structured fields, e.g. risk_assessment)
        action = getattr(recommendation, "recommended_action", RecommendedAction.NO_ACTION)
        
        if action in (RecommendedAction.DELETE_VOLUME, RecommendedAction.TERMINATE_INSTANCE):
            risk = getattr(recommendation, "risk_assessment", {}) or {}
            
            # Require structured flag confirmation: risk_assessment.backup_verified == True or risk_assessment.snapshot_created == True
            backup_verified = False
            if risk.get("backup_verified") is True or risk.get("snapshot_created") is True or risk.get("ami_created") is True:
                backup_verified = True
                
            if not backup_verified:
                violations.append(
                    f"[Blocked] ProductionGuardRule: Condition 'BackupVerification' triggered (destructive action {action.value} lacks structured backup confirmation in risk_assessment). "
                    f"Recommended operator action: Create a backup snapshot/AMI before initiating remediation."
                )

        return violations if violations else True
