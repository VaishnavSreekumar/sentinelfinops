"""
Unit tests for abstract LLM provider layer and MockProvider.
"""
import unittest
import uuid
from unittest.mock import patch, MagicMock
from typing import Literal, Optional, List, Dict, Union
from enum import Enum
from pydantic import BaseModel, Field

from ai.providers.base import LLMProvider
from ai.providers.factory import LLMProviderFactory
from ai.providers.mock_provider import MockProvider
from ai.providers.openai import OpenAIProvider, OpenAIProviderError
from ai.contracts.recommendation import RecommendationV1, RecommendationV2
from ai.contracts.telemetry import TelemetryRecord
from ai.contracts.enums import RecommendedAction, PolicyValidationStatus

class TestEnum(Enum):
    ALPHA = "ALPHA"
    BETA = "BETA"

class NestedModel(BaseModel):
    name: str
    value: int = 42

class CustomTestModel(BaseModel):
    id: uuid.UUID
    name: str
    score: float
    is_active: bool
    status: TestEnum
    version: Literal["1.0.0"] = "1.0.0"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)
    nested: NestedModel
    optional_field: Optional[str] = None
    union_field: Union[int, None]

class TestProviders(unittest.TestCase):
    def test_abstract_class_instantiation(self):
        """Assert that attempting to instantiate LLMProvider directly raises a TypeError."""
        with self.assertRaises(TypeError):
            LLMProvider(model_id="test-model", config={}) # type: ignore

    def test_factory_resolve_mock(self):
        """Verify that passing 'mock' returns a correctly configured MockProvider instance."""
        provider = LLMProviderFactory.create(
            provider_name="mock",
            model_id="mock-gpt",
            config={"temperature": 0.0}
        )
        self.assertIsInstance(provider, MockProvider)
        self.assertEqual(provider.model_id, "mock-gpt")
        self.assertEqual(provider.config, {"temperature": 0.0})

    def test_factory_error_handling(self):
        """Ensure passing unknown names raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            LLMProviderFactory.create(
                provider_name="bedrock",
                model_id="claude-3",
                config={}
            )
        self.assertIn("Unknown LLM provider name: 'bedrock'", str(ctx.exception))

    def test_mock_provider_type_validation(self):
        """Assert that invoke raises TypeError if schema is not a subclass of BaseModel."""
        provider = MockProvider(model_id="mock-model", config={})
        with self.assertRaises(TypeError):
            provider.invoke("test prompt", dict) # type: ignore

    def test_mock_provider_recommendation_v1(self):
        """Request RecommendationV1: Assert returned instance is RecommendationV1 and conformed."""
        provider = MockProvider(model_id="v1-model", config={})
        res = provider.invoke("Optimize EBS", RecommendationV1)
        self.assertIsInstance(res, RecommendationV1)
        self.assertEqual(res.schema_version, "1.0.0")
        self.assertEqual(res.model, "v1-model")
        self.assertTrue(res.resource_id.startswith("mock_"))
        self.assertIsInstance(res.recommendation_id, uuid.UUID)
        self.assertIsInstance(res.recommended_action, RecommendedAction)
        self.assertIsInstance(res.confidence_score, float)
        self.assertIsInstance(res.explanation_steps, list)

    def test_mock_provider_recommendation_v2(self):
        """Request RecommendationV2: Assert returned instance is RecommendationV2 and conformed."""
        provider = MockProvider(model_id="v2-model", config={})
        res = provider.invoke("Optimize EBS V2", RecommendationV2)
        self.assertIsInstance(res, RecommendationV2)
        self.assertEqual(res.schema_version, "2.0.0")
        self.assertEqual(res.model, "v2-model")
        self.assertIsInstance(res.alternative_actions, list)
        self.assertEqual(res.operational_impact, "NONE")

    def test_mock_provider_telemetry_record(self):
        """Request TelemetryRecord: Assert returned instance is TelemetryRecord."""
        provider = MockProvider(model_id="telemetry-model", config={})
        res = provider.invoke("Log telemetry", TelemetryRecord)
        self.assertIsInstance(res, TelemetryRecord)
        self.assertEqual(res.schema_version, "1.0.0")
        self.assertIsInstance(res.request_id, uuid.UUID)
        self.assertIsInstance(res.execution_id, uuid.UUID)
        self.assertIsInstance(res.validation_status, PolicyValidationStatus)

    def test_mock_provider_custom_model(self):
        """Request a custom test BaseModel: Verify it matches custom fields."""
        provider = MockProvider(model_id="custom-model", config={})
        res = provider.invoke("Generate custom", CustomTestModel)
        self.assertIsInstance(res, CustomTestModel)
        self.assertIsInstance(res.id, uuid.UUID)
        self.assertEqual(res.name, "mock_name")
        self.assertEqual(res.score, 1.0)
        self.assertEqual(res.is_active, False)
        self.assertEqual(res.status, TestEnum.ALPHA)
        self.assertEqual(res.version, "1.0.0")
        self.assertEqual(res.tags, [])
        self.assertEqual(res.metadata, {})
        self.assertIsInstance(res.nested, NestedModel)
        self.assertEqual(res.nested.name, "mock_name")
        self.assertEqual(res.nested.value, 42)
        self.assertEqual(res.optional_field, None)
        self.assertEqual(res.union_field, 1)

class TestOpenAIProvider(unittest.TestCase):
    @patch("ai.providers.openai.OpenAI")
    def test_openai_provider_initialization(self, mock_openai_class):
        """Verify that passing optional configs properly sets client keyword args."""
        config = {
            "api_key": "test-key",
            "base_url": "https://test-api.openai.com",
            "timeout": 10.0,
            "max_retries": 3
        }
        provider = OpenAIProvider(model_id="gpt-4", config=config)
        mock_openai_class.assert_called_once_with(
            api_key="test-key",
            base_url="https://test-api.openai.com",
            timeout=10.0,
            max_retries=3
        )

    @patch("ai.providers.openai.OpenAI")
    def test_openai_provider_invoke_success(self, mock_openai_class):
        """Test successful schema parsing with mocked parse response."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.parsed = CustomTestModel(
            id=uuid.uuid4(),
            name="custom_success",
            score=99.9,
            is_active=True,
            status=TestEnum.BETA,
            nested=NestedModel(name="sub", value=100),
            union_field=5
        )
        mock_choice.message.refusal = None
        mock_completion.choices = [mock_choice]
        mock_client.beta.chat.completions.parse.return_value = mock_completion
        
        provider = OpenAIProvider(model_id="gpt-4o", config={"api_key": "fake-key"})
        res = provider.invoke("test prompt", CustomTestModel)
        
        self.assertEqual(res.name, "custom_success")
        self.assertEqual(res.score, 99.9)
        self.assertEqual(res.status, TestEnum.BETA)
        self.assertEqual(res.nested.value, 100)
        
        mock_client.beta.chat.completions.parse.assert_called_once_with(
            model="gpt-4o",
            messages=[{"role": "user", "content": "test prompt"}],
            response_format=CustomTestModel
        )

    @patch("ai.providers.openai.OpenAI")
    def test_openai_provider_invoke_type_error(self, mock_openai_class):
        """Verify that passing a non-BaseModel schema raises a TypeError."""
        provider = OpenAIProvider(model_id="gpt-4o", config={})
        with self.assertRaises(TypeError):
            provider.invoke("test prompt", dict)  # type: ignore

    @patch("ai.providers.openai.OpenAI")
    def test_openai_provider_invoke_refusal(self, mock_openai_class):
        """Test model refusal raises OpenAIProviderError."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.parsed = None
        mock_choice.message.refusal = "I cannot process this prompt."
        mock_completion.choices = [mock_choice]
        mock_client.beta.chat.completions.parse.return_value = mock_completion
        
        provider = OpenAIProvider(model_id="gpt-4", config={})
        with self.assertRaises(OpenAIProviderError) as ctx:
            provider.invoke("test prompt", CustomTestModel)
        self.assertIn("OpenAI provider refusal occurred: I cannot process this prompt.", str(ctx.exception))

    @patch("ai.providers.openai.OpenAI")
    def test_openai_provider_invoke_empty_response(self, mock_openai_class):
        """Test empty parsed response raises OpenAIProviderError."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.parsed = None
        mock_choice.message.refusal = None
        mock_completion.choices = [mock_choice]
        mock_client.beta.chat.completions.parse.return_value = mock_completion
        
        provider = OpenAIProvider(model_id="gpt-4", config={})
        with self.assertRaises(OpenAIProviderError) as ctx:
            provider.invoke("test prompt", CustomTestModel)
        self.assertIn("OpenAI provider returned empty parsed completion response.", str(ctx.exception))

    @patch("ai.providers.openai.OpenAI")
    def test_openai_provider_invoke_sdk_exception(self, mock_openai_class):
        """Test SDK exceptions are caught and wrapped in OpenAIProviderError."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        import openai
        mock_client.beta.chat.completions.parse.side_effect = openai.APIConnectionError(
            message="Connection failed",
            request=MagicMock()
        )
        
        provider = OpenAIProvider(model_id="gpt-4", config={})
        with self.assertRaises(OpenAIProviderError) as ctx:
            provider.invoke("test prompt", CustomTestModel)
        self.assertIn("OpenAI provider invocation failed", str(ctx.exception))
        self.assertIsInstance(ctx.exception.__cause__, openai.APIConnectionError)

    @patch("ai.providers.openai.OpenAI")
    def test_openai_provider_invoke_validation_failure(self, mock_openai_class):
        """Test Pydantic validation failure is caught and wrapped in OpenAIProviderError."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        from pydantic import ValidationError
        try:
            raise ValidationError.from_exception_data(
                "CustomTestModel",
                [{"type": "missing", "loc": ("name",), "input": {}}]
            )
        except ValidationError as e:
            validation_error = e
            
        mock_client.beta.chat.completions.parse.side_effect = validation_error
        
        provider = OpenAIProvider(model_id="gpt-4", config={})
        with self.assertRaises(OpenAIProviderError) as ctx:
            provider.invoke("test prompt", CustomTestModel)
        self.assertIn("OpenAI provider invocation failed", str(ctx.exception))
        self.assertIsInstance(ctx.exception.__cause__, ValidationError)
