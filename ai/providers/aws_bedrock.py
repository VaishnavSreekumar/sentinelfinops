"""
AWS Bedrock LLM Provider implementation.
"""
from ai.providers.base import BaseLLMProvider

class AWSBedrockProvider(BaseLLMProvider):
    """
    Bedrock client wrapper interface.
    """
    def invoke(self, system: str, user: str, schema):
        raise NotImplementedError("AWSBedrockProvider.invoke is not implemented yet")
