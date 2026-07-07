"""
Unit tests for ProductionGuardRule verifying environment, owner, confidence,
critical naming patterns, and structured backup protections.
"""
import unittest
import uuid

from ai.contracts.scan_context import ScanContext
from ai.contracts.owner_info import OwnerInfo
from ai.contracts.enums import ResourceType, RecommendedAction
from ai.contracts.recommendation import RecommendationV1
from policy.rules.production_guard import ProductionGuardRule

class TestProductionGuardRule(unittest.TestCase):
    def setUp(self):
        self.rule = ProductionGuardRule()
        
        # Base valid scan context (Development environment, owner set, non-critical name)
        self.valid_context = ScanContext(
            execution_id=uuid.uuid4(),
            resource_id="i-test-dev",
            resource_type=ResourceType.EC2,
            raw_resource={
                "instance_name": "app-dev-server",
                "tags": [
                    {"Key": "Environment", "Value": "Development"},
                    {"Key": "Owner", "Value": "dev-team"}
                ]
            },
            owner_info=OwnerInfo(owner_arn="arn:aws:iam::123456789012:user/dev-user"),
            account_id="123456789012",
            account_name="DevSandboxAccount",
            region="us-east-1"
        )
        
        # Base valid high-confidence recommendation
        self.valid_recommendation = RecommendationV1(
            recommendation_id=uuid.uuid4(),
            generated_at="2026-07-07T00:00:00Z",
            model="gpt-4",
            prompt_version="1.0.0",
            resource_id="i-test-dev",
            recommended_action=RecommendedAction.STOP_INSTANCE,
            reasoning="Instance is idle. We should stop it to save costs.",
            confidence_score=0.95,
            risk_assessment={"disruption": "low", "backup_verified": True},
            projected_monthly_savings=15.0,
            explanation_steps=["Stop instance"],
            citations=["cpu_idle"],
            confidence_reason="CPU is consistently under 1.0%",
            assumptions=["Not critical"]
        )

    def test_pass_valid_dev_resource(self):
        """Assert that a standard development resource with resolved owner and high confidence passes."""
        result = self.rule.evaluate(self.valid_recommendation, self.valid_context)
        self.assertEqual(result, True)

    def test_block_missing_context(self):
        """Verify that a missing context fails closed with a violation list."""
        result = self.rule.evaluate(self.valid_recommendation, None)
        self.assertIsInstance(result, list)
        self.assertTrue(any("Condition 'ContextVerification'" in v for v in result))

    def test_block_low_confidence(self):
        """Assert that confidence below 0.90 blocks the action."""
        rec = self.valid_recommendation.model_copy(update={"confidence_score": 0.85})
        result = self.rule.evaluate(rec, self.valid_context)
        self.assertIsInstance(result, list)
        self.assertTrue(any("Condition 'ConfidenceScore'" in v for v in result))
        self.assertTrue(any("score 0.85 is below" in v for v in result))

    def test_configurable_confidence_threshold(self):
        """Assert that the confidence threshold can be loaded dynamically from configuration."""
        custom_rule = ProductionGuardRule(config={"ai": {"min_confidence_threshold": 0.98}})
        
        # 0.95 is above default 0.90 but below custom threshold of 0.98
        rec = self.valid_recommendation.model_copy(update={"confidence_score": 0.95})
        result = custom_rule.evaluate(rec, self.valid_context)
        self.assertIsInstance(result, list)
        self.assertTrue(any("score 0.95 is below minimum threshold of 0.98" in v for v in result))

    def test_block_production_env(self):
        """Assert that a resource with environment tag set to Production/Prod is blocked."""
        raw_res = self.valid_context.raw_resource.copy()
        raw_res["tags"] = [
            {"Key": "Environment", "Value": "Production"},
            {"Key": "Owner", "Value": "dev-team"}
        ]
        ctx = self.valid_context.model_copy(update={"raw_resource": raw_res})
        result = self.rule.evaluate(self.valid_recommendation, ctx)
        self.assertIsInstance(result, list)
        self.assertTrue(any("Condition 'EnvironmentIsolation'" in v for v in result))
        self.assertTrue(any("Production environment detected" in v for v in result))

    def test_block_prod_account(self):
        """Assert that a resource inside a Production account is blocked even if environment tag is missing."""
        raw_res = self.valid_context.raw_resource.copy()
        raw_res["tags"] = [
            {"Key": "Owner", "Value": "dev-team"}
        ]
        ctx = self.valid_context.model_copy(update={"account_name": "ProductionBillingAccount", "raw_resource": raw_res})
        result = self.rule.evaluate(self.valid_recommendation, ctx)
        self.assertIsInstance(result, list)
        self.assertTrue(any("Production account" in v for v in result))

    def test_block_unknown_env(self):
        """Assert that missing environment metadata is blocked (required metadata check)."""
        raw_res = self.valid_context.raw_resource.copy()
        raw_res["tags"] = [
            {"Key": "Owner", "Value": "dev-team"}
        ]
        ctx = self.valid_context.model_copy(update={"raw_resource": raw_res})
        result = self.rule.evaluate(self.valid_recommendation, ctx)
        self.assertIsInstance(result, list)
        self.assertTrue(any("Condition 'EnvironmentIsolation'" in v for v in result))
        self.assertTrue(any("environment tag is missing" in v for v in result))

    def test_block_critical_naming(self):
        """Assert that resource names containing critical keywords (e.g. database, database-server) are blocked."""
        raw_res = self.valid_context.raw_resource.copy()
        raw_res["instance_name"] = "auth-db-primary"
        ctx = self.valid_context.model_copy(update={"raw_resource": raw_res})
        result = self.rule.evaluate(self.valid_recommendation, ctx)
        self.assertIsInstance(result, list)
        self.assertTrue(any("Condition 'CriticalNaming'" in v for v in result))
        self.assertTrue(any("contains sensitive keyword 'db'" in v or "contains sensitive keyword 'database'" in v for v in result))

    def test_block_missing_owner(self):
        """Assert that a resource without owner attribution is blocked."""
        raw_res = self.valid_context.raw_resource.copy()
        raw_res["tags"] = [
            {"Key": "Environment", "Value": "Development"}
        ]
        ctx = self.valid_context.model_copy(update={"owner_info": OwnerInfo(), "raw_resource": raw_res})
        result = self.rule.evaluate(self.valid_recommendation, ctx)
        self.assertIsInstance(result, list)
        self.assertTrue(any("Condition 'OwnerVerification'" in v for v in result))

    def test_block_destructive_ebs_no_snapshot(self):
        """Assert that DELETE_VOLUME is blocked if structured backup confirmation is missing from risk_assessment."""
        rec = self.valid_recommendation.model_copy(update={
            "recommended_action": RecommendedAction.DELETE_VOLUME,
            "risk_assessment": {"disruption": "low"}
        })
        result = self.rule.evaluate(rec, self.valid_context)
        self.assertIsInstance(result, list)
        self.assertTrue(any("Condition 'BackupVerification'" in v for v in result))
        self.assertTrue(any("lacks structured backup confirmation" in v for v in result))

    def test_pass_destructive_ebs_with_snapshot(self):
        """Assert that DELETE_VOLUME passes if snapshot confirmation is verified in structured risk_assessment."""
        rec = self.valid_recommendation.model_copy(update={
            "recommended_action": RecommendedAction.DELETE_VOLUME,
            "risk_assessment": {"disruption": "low", "snapshot_created": True}
        })
        result = self.rule.evaluate(rec, self.valid_context)
        self.assertEqual(result, True)

    def test_explainability_formatting(self):
        """Assert that policy violation outputs follow a structured, machine-readable explainability format."""
        rec = self.valid_recommendation.model_copy(update={"confidence_score": 0.80})
        result = self.rule.evaluate(rec, self.valid_context)
        self.assertIsInstance(result, list)
        
        violation = result[0]
        self.assertTrue(violation.startswith("[Blocked] ProductionGuardRule: Condition '"))
        self.assertIn("triggered (", violation)
        self.assertIn("). Recommended operator action: ", violation)

if __name__ == "__main__":
    unittest.main()
