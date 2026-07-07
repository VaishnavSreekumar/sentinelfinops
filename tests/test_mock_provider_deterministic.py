"""
Unit tests for deterministic MockProvider recommendations, schema validation,
policy engine validation, and provider factory switching.
"""
import unittest
import json
import uuid
import os
from unittest.mock import patch, MagicMock

from ai.providers.mock_provider import MockProvider
from ai.providers.factory import LLMProviderFactory
from ai.contracts.recommendation import RecommendationV1
from ai.contracts.enums import RecommendedAction
from policy.engine import PolicyEngine
from policy.rules.production_guard import ProductionGuardRule

class TestDeterministicMockProvider(unittest.TestCase):
    def setUp(self):
        self.provider = MockProvider(model_id="mock-gpt-4", config={})

    def _build_prompt(self, resource_id, resource_type, cpu_mean, current_cost):
        context = {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "metrics_summary": {
                "cpu_mean_7_days": cpu_mean,
                "cpu_max_7_days": cpu_mean * 1.5,
                "current_cost": current_cost,
                "projected_savings": current_cost
            },
            "tags": {
                "Name": "test-resource",
                "Environment": "Production",
                "Owner": "finops-team"
            }
        }
        return f"System:\nSystemPrompt\n\nUser:\nUserPrompt\n\nContext:\n{json.dumps(context)}"

    def test_mock_provider_idle_ec2(self):
        """Verify that an idle EC2 instance (CPU < 1.0) returns a STOP_INSTANCE action with 0.98 confidence."""
        prompt = self._build_prompt("i-12345", "EC2", 0.4, 20.0)
        recommendation = self.provider.invoke(prompt, RecommendationV1)

        self.assertEqual(recommendation.recommended_action, RecommendedAction.STOP_INSTANCE)
        self.assertEqual(recommendation.confidence_score, 0.98)
        self.assertEqual(recommendation.projected_monthly_savings, 20.0)
        self.assertIn("CPU utilisation has remained below 1%", recommendation.reasoning)
        self.assertEqual(recommendation.resource_id, "i-12345")
        self.assertEqual(recommendation.schema_version, "1.0.0")

    def test_mock_provider_underutilized_ec2(self):
        """Verify that an underutilized EC2 (1.0 <= CPU < 5.0) returns a RESIZE_INSTANCE action with 0.91 confidence."""
        prompt = self._build_prompt("i-67890", "EC2", 2.5, 50.0)
        recommendation = self.provider.invoke(prompt, RecommendationV1)

        self.assertEqual(recommendation.recommended_action, RecommendedAction.RESIZE_INSTANCE)
        self.assertEqual(recommendation.confidence_score, 0.91)
        self.assertEqual(recommendation.projected_monthly_savings, 25.0) # 50 / 2
        self.assertIn("moving to a smaller instance type", recommendation.reasoning)
        self.assertEqual(recommendation.resource_id, "i-67890")

    def test_mock_provider_active_ec2(self):
        """Verify that active EC2 (CPU >= 5.0) returns NO_ACTION."""
        prompt = self._build_prompt("i-active", "EC2", 12.0, 100.0)
        recommendation = self.provider.invoke(prompt, RecommendationV1)

        self.assertEqual(recommendation.recommended_action, RecommendedAction.NO_ACTION)
        self.assertEqual(recommendation.projected_monthly_savings, 0.0)
        self.assertIn("No remediation action is required", recommendation.reasoning)

    def test_mock_provider_idle_ebs(self):
        """Verify that an unattached EBS volume returns a DELETE_VOLUME action with 0.95 confidence."""
        prompt = self._build_prompt("vol-abcde", "EBS", 0.0, 8.0)
        recommendation = self.provider.invoke(prompt, RecommendationV1)

        self.assertEqual(recommendation.recommended_action, RecommendedAction.DELETE_VOLUME)
        self.assertEqual(recommendation.confidence_score, 0.95)
        self.assertEqual(recommendation.projected_monthly_savings, 8.0)
        self.assertIn("Volume has not been attached within the observation window", recommendation.reasoning)

    def test_mock_provider_determinism(self):
        """Assert that consecutive invocations with the same context return identical output."""
        prompt = self._build_prompt("i-det", "EC2", 0.2, 30.0)
        rec1 = self.provider.invoke(prompt, RecommendationV1)
        rec2 = self.provider.invoke(prompt, RecommendationV1)

        self.assertEqual(rec1.recommendation_id, rec2.recommendation_id)
        self.assertEqual(rec1.recommended_action, rec2.recommended_action)
        self.assertEqual(rec1.confidence_score, rec2.confidence_score)
        self.assertEqual(rec1.reasoning, rec2.reasoning)
        self.assertEqual(rec1.generated_at, rec2.generated_at)

    def test_provider_switching_factory(self):
        """Verify that provider factory handles environment overrides correctly."""
        # 1. Test mock selection
        with patch.dict(os.environ, {"OPENAI_PROVIDER": "mock"}):
            provider = LLMProviderFactory.create("mock", "gpt-mock", {})
            self.assertIsInstance(provider, MockProvider)

        # 2. Test openai selection
        with patch.dict(os.environ, {"OPENAI_PROVIDER": "openai"}):
            provider = LLMProviderFactory.create("openai", "gpt-4", {"api_key": "test"})
            from ai.providers.openai import OpenAIProvider
            self.assertIsInstance(provider, OpenAIProvider)

    def test_policy_engine_flow(self):
        """Verify that mock recommendations flow through the policy engine correctly."""
        prompt = self._build_prompt("i-prod", "EC2", 0.5, 40.0)
        recommendation = self.provider.invoke(prompt, RecommendationV1)

        from ai.contracts.enums import PolicyValidationStatus
        from policy.rules.base_rule import PolicyRule
        
        class LocalPassRule(PolicyRule):
            name = "LocalPassRule"
            def evaluate(self, rec, ctx):
                return True

        engine = PolicyEngine(rules=[LocalPassRule()])
        result = engine.evaluate(recommendation)
        
        self.assertEqual(result.status, PolicyValidationStatus.PASSED)

if __name__ == "__main__":
    unittest.main()
