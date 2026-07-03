"""
Direct Anthropic API LLM Provider implementation.
"""
from ai.providers.base import BaseLLMProvider

class AnthropicProvider(BaseLLMProvider):
    """
    Direct Anthropic API client wrapper.
    """
    def invoke(self, system: str, user: str, schema):
        raise NotImplementedError("AnthropicProvider.invoke is not implemented yet")
