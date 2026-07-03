"""
Unit tests for the Policy Engine Integration.
"""
import unittest
from uuid import uuid4
from datetime import datetime

from ai.contracts.recommendation import RecommendationV1
from ai.contracts.enums import RecommendedAction, PolicyValidationStatus, RiskLevel
from policy.engine import PolicyEngine
from policy.rules.base_rule import PolicyRule

class MockPassRule(PolicyRule):
    name = "MockPassRule"
    def evaluate(self, recommendation, context):
        return True

class MockFailRule(PolicyRule):
    name = "MockFailRule"
    def evaluate(self, recommendation, context):
        return ["Violation 1", "Violation 2"]

class MockCrashRule(PolicyRule):
    name = "MockCrashRule"
    def evaluate(self, recommendation, context):
        raise ValueError("Simulated rule crash")

class TestPolicyEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.recommendation = RecommendationV1(
            recommendation_id=uuid4(),
            generated_at=datetime.utcnow().isoformat() + "Z",
            model="gpt-4o",
            prompt_version="1.0.0",
            resource_id="vol-1234",
            recommended_action=RecommendedAction.DELETE_VOLUME,
            reasoning="Volume has been unattached for 30 days.",
            confidence_score=0.95,
            risk_assessment={"data_loss": "low"},
            projected_monthly_savings=50.0,
            explanation_steps=["Step 1", "Step 2"],
            citations=["ops-metric-1"],
            confidence_reason="No Read/Write ops.",
            assumptions=["No snapshot dependency"]
        )

    def test_all_rules_pass(self) -> None:
        """Verify that when all rules pass, the validation status is PASSED."""
        engine = PolicyEngine(rules=[MockPassRule(), MockPassRule()])
        result = engine.evaluate(self.recommendation)

        self.assertEqual(result.status, PolicyValidationStatus.PASSED)
        self.assertEqual(result.rule_name, "PolicyEngine")
        self.assertEqual(result.severity, RiskLevel.LOW.value)
        self.assertEqual(result.violations, [])
        self.assertEqual(result.passed_rules, ["MockPassRule", "MockPassRule"])
        self.assertEqual(result.failed_rules, [])
        self.assertTrue(result.timestamp.endswith("Z"))

    def test_single_rule_fails(self) -> None:
        """Verify that when a single rule fails, status is FAILED and violations are collected."""
        engine = PolicyEngine(rules=[MockPassRule(), MockFailRule()])
        result = engine.evaluate(self.recommendation)

        self.assertEqual(result.status, PolicyValidationStatus.FAILED)
        self.assertEqual(result.rule_name, "MockFailRule")
        self.assertEqual(result.severity, RiskLevel.CRITICAL.value)
        self.assertEqual(result.violations, ["Violation 1", "Violation 2"])
        self.assertEqual(result.passed_rules, ["MockPassRule"])
        self.assertEqual(result.failed_rules, ["MockFailRule"])

    def test_aggregate_evaluation_multiple_failures(self) -> None:
        """Verify aggregate evaluation collects all violations and failed rules in one run."""
        rule_fail_1 = MockFailRule()
        rule_fail_1.name = "MockFailRule1"
        rule_fail_2 = MockFailRule()
        rule_fail_2.name = "MockFailRule2"

        engine = PolicyEngine(rules=[rule_fail_1, MockPassRule(), rule_fail_2])
        result = engine.evaluate(self.recommendation)

        self.assertEqual(result.status, PolicyValidationStatus.FAILED)
        self.assertEqual(result.rule_name, "MockFailRule1")  # First failed rule name
        self.assertEqual(result.severity, RiskLevel.CRITICAL.value)
        self.assertEqual(result.violations, ["Violation 1", "Violation 2", "Violation 1", "Violation 2"])
        self.assertEqual(result.passed_rules, ["MockPassRule"])
        self.assertEqual(result.failed_rules, ["MockFailRule1", "MockFailRule2"])

    def test_rule_crash_fails_closed(self) -> None:
        """Verify that if a rule raises an exception, policy validation fails closed (status is FAILED)."""
        engine = PolicyEngine(rules=[MockPassRule(), MockCrashRule(), MockFailRule()])
        result = engine.evaluate(self.recommendation)

        self.assertEqual(result.status, PolicyValidationStatus.FAILED)
        self.assertEqual(result.rule_name, "MockCrashRule")
        self.assertEqual(result.severity, RiskLevel.CRITICAL.value)
        self.assertIn("MockCrashRule", result.failed_rules)
        self.assertIn("MockFailRule", result.failed_rules)
        self.assertTrue(any("Simulated rule crash" in v for v in result.violations))

    def test_recommendation_is_not_mutated(self) -> None:
        """Verify that the RecommendationV1 input object is never mutated by the engine."""
        original_dict = self.recommendation.model_dump()

        engine = PolicyEngine(rules=[MockPassRule(), MockFailRule(), MockCrashRule()])
        _ = engine.evaluate(self.recommendation)

        self.assertEqual(self.recommendation.model_dump(), original_dict)

    def test_deterministic_behavior(self) -> None:
        """Verify that evaluating the same recommendation multiple times yields identical results."""
        engine = PolicyEngine(rules=[MockPassRule(), MockFailRule(), MockCrashRule()])
        
        result_1 = engine.evaluate(self.recommendation)
        result_2 = engine.evaluate(self.recommendation)

        # Exclude timestamp since datetime.utcnow() changes across execution calls
        self.assertEqual(result_1.status, result_2.status)
        self.assertEqual(result_1.rule_name, result_2.rule_name)
        self.assertEqual(result_1.severity, result_2.severity)
        self.assertEqual(result_1.violations, result_2.violations)
        self.assertEqual(result_1.passed_rules, result_2.passed_rules)
        self.assertEqual(result_1.failed_rules, result_2.failed_rules)
