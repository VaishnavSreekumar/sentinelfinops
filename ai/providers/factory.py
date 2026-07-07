"""
LLM Provider Factory implementation.
"""
from ai.providers.base import LLMProvider
from ai.providers.mock_provider import MockProvider

class LLMProviderFactory:
    """
    Factory for instantiating LLMProvider implementations.
    """
    @staticmethod
    def create(provider_name: str, model_id: str, config: dict) -> LLMProvider:
        """
        Creates and returns an instance of LLMProvider based on provider_name.
        """
        if provider_name.lower() == "mock":
            return MockProvider(model_id=model_id, config=config)
        elif provider_name.lower() == "openai":
            from ai.providers.openai import OpenAIProvider
            return OpenAIProvider(model_id=model_id, config=config)
        elif provider_name.lower() == "gemini":
            from ai.providers.gemini import GeminiProvider
            return GeminiProvider(model_id=model_id, config=config)
        
        raise ValueError(f"Unknown LLM provider name: '{provider_name}'")
