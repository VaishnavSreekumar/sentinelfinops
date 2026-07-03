"""
Ollama Local LLM Provider implementation.
"""
from ai.providers.base import BaseLLMProvider

class OllamaProvider(BaseLLMProvider):
    """
    Local Ollama runner client wrapper.
    """
    def invoke(self, system: str, user: str, schema):
        raise NotImplementedError("OllamaProvider.invoke is not implemented yet")
