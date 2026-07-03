"""
Unit tests for the AI Gateway orchestration layer.
"""
import unittest
from unittest.mock import MagicMock
from ai.gateway import AIGateway
from ai.prompts.registry import PromptTemplate, PromptNotFoundError
from ai.contracts.resource_context import ResourceContextV1
from ai.contracts.recommendation import RecommendationV1
from ai.contracts.enums import RecommendedAction, ResourceType, CloudProvider

class TestAIGateway(unittest.TestCase):
    def setUp(self):
        self.mock_registry = MagicMock()
        self.mock_provider = MagicMock()
        self.gateway = AIGateway(
            provider=self.mock_provider,
            prompt_registry=self.mock_registry
        )

    def test_gateway_initialization(self):
        """Verify that provider and prompt_registry are correctly bound via dependency injection."""
        self.assertIs(self.gateway.provider, self.mock_provider)
        self.assertIs(self.gateway.registry, self.mock_registry)

    def test_execute_reasoning_success_and_composed_prompt(self):
        """Verify successful reasoning flow and check that composed prompt structure is exact."""
        # 1. Mock registry to return a prompt template
        mock_template = PromptTemplate(
            name="test_prompt",
            version="1.0.0",
            system_prompt="System instructions.",
            user_prompt="User input template."
        )
        self.mock_registry.get_prompt.return_value = mock_template
        
        # 2. Mock provider to return RecommendationV1
        mock_rec = RecommendationV1(
            model="mock",
            prompt_version="1.0.0",
            resource_id="vol-1234",
            recommended_action=RecommendedAction.DELETE_VOLUME,
            reasoning="idle volume detected",
            confidence_score=0.9,
            risk_assessment={},
            projected_monthly_savings=15.5,
            confidence_reason="no operations for 30 days"
        )
        self.mock_provider.invoke.return_value = mock_rec
        
        # 3. Create a ResourceContextV1 context
        context = ResourceContextV1(
            resource_id="vol-1234",
            resource_type=ResourceType.EBS,
            cloud_provider=CloudProvider.AWS,
            account_id="123456789012",
            account_name="test-account",
            region="us-east-1",
            state="available",
            tags={"Name": "IdleVol"},
            metrics_summary={"VolumeReadOps": 0, "VolumeWriteOps": 0},
            lifecycle_details={},
            history_summary={}
        )
        
        # 4. Call gateway execute_reasoning
        res = self.gateway.execute_reasoning(
            context=context,
            prompt_name="test_prompt",
            prompt_version="1.0.0"
        )
        
        # 5. Assert template is loaded with correct name and version
        self.mock_registry.get_prompt.assert_called_once_with("test_prompt", "1.0.0")
        
        # 6. Verify provider is invoked with the exact composed prompt and RecommendationV1
        self.mock_provider.invoke.assert_called_once()
        call_args = self.mock_provider.invoke.call_args[0]
        final_prompt = call_args[0]
        schema = call_args[1]
        
        self.assertEqual(schema, RecommendationV1)
        
        # Assert exact prompt formatting structure:
        expected_prompt = (
            f"System:\nSystem instructions.\n\n"
            f"User:\nUser input template.\n\n"
            f"Context:\n{context.model_dump_json()}"
        )
        self.assertEqual(final_prompt, expected_prompt)
        
        # Verify returned recommendation is unchanged
        self.assertIs(res, mock_rec)

    def test_execute_reasoning_type_error(self):
        """Assert TypeError is raised if context is not ResourceContextV1."""
        with self.assertRaises(TypeError):
            self.gateway.execute_reasoning(
                context={},  # type: ignore
                prompt_name="test",
                prompt_version="1.0.0"
            )

    def test_execute_reasoning_registry_error_propagation(self):
        """Assert PromptRegistry errors propagate without being caught or modified."""
        self.mock_registry.get_prompt.side_effect = PromptNotFoundError("Missing prompt")
        context = ResourceContextV1(
            resource_id="vol-123", resource_type=ResourceType.EBS, cloud_provider=CloudProvider.AWS,
            account_id="123", account_name="acc", region="us-east-1", state="available"
        )
        with self.assertRaises(PromptNotFoundError):
            self.gateway.execute_reasoning(context, "test", "1.0.0")

    def test_execute_reasoning_provider_error_propagation(self):
        """Assert LLMProvider errors propagate without being caught or modified."""
        mock_template = PromptTemplate(
            name="test", version="1.0.0", system_prompt="sys", user_prompt="usr"
        )
        self.mock_registry.get_prompt.return_value = mock_template
        self.mock_provider.invoke.side_effect = ValueError("Provider connection failed")
        
        context = ResourceContextV1(
            resource_id="vol-123", resource_type=ResourceType.EBS, cloud_provider=CloudProvider.AWS,
            account_id="123", account_name="acc", region="us-east-1", state="available"
        )
        with self.assertRaises(ValueError) as ctx:
            self.gateway.execute_reasoning(context, "test", "1.0.0")
        self.assertEqual(str(ctx.exception), "Provider connection failed")
