"""
Policy Engine implementation.
Intercepts outputs and checks compliance rules.
"""
from datetime import datetime
from typing import List, Any
from ai.contracts.recommendation import RecommendationV1
from ai.contracts.policy_result import PolicyValidationResult
from ai.contracts.enums import PolicyValidationStatus, RiskLevel

class PolicyEngine:
    """
    Orchestrates the evaluation of Recommendation items against policy rules.
    """
    def __init__(self, rules: list) -> None:
        self.rules = rules or []

    def evaluate(self, recommendation: RecommendationV1) -> PolicyValidationResult:
        """
        Evaluates a recommendation against the deterministic rules.
        Runs all rules (aggregate evaluation) and returns a PolicyValidationResult.
        """
        passed_rules: List[str] = []
        failed_rules: List[str] = []
        violations: List[str] = []

        # Enforce aggregate execution. Evaluate all rules, catching any rule crashes
        # to guarantee deterministic policy failure (fail closed).
        for rule in self.rules:
            rule_name = getattr(rule, "name", rule.__class__.__name__)
            try:
                # Call evaluate exactly matching the legacy rule interface signature
                result = rule.evaluate(recommendation, None)
                
                # If result is False or contains violation strings, it fails.
                # If it returns True, None, or an empty list, it passes.
                if result is False:
                    failed_rules.append(rule_name)
                    violations.append(f"Rule '{rule_name}' failed validation.")
                elif isinstance(result, (list, tuple)):
                    str_violations = [str(v) for v in result if v]
                    if str_violations:
                        failed_rules.append(rule_name)
                        violations.extend(str_violations)
                    else:
                        passed_rules.append(rule_name)
                else:
                    passed_rules.append(rule_name)
            except Exception as e:
                # Treat rule crashes as deterministic policy failures (fail closed)
                failed_rules.append(rule_name)
                violations.append(f"Rule '{rule_name}' failed execution: {str(e)}")

        # Calculate result status, severity, and first failed rule name
        if failed_rules:
            status = PolicyValidationStatus.FAILED
            severity = RiskLevel.CRITICAL.value
            rule_name = failed_rules[0]
        else:
            status = PolicyValidationStatus.PASSED
            severity = RiskLevel.LOW.value
            rule_name = "PolicyEngine"

        # Generate timestamp as required by the contract
        timestamp = datetime.utcnow().isoformat() + "Z"

        return PolicyValidationResult(
            status=status,
            rule_name=rule_name,
            severity=severity,
            violations=violations,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            timestamp=timestamp
        )
