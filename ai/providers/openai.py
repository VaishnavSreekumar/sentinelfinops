"""
OpenAI API LLM Provider implementation using Structured Outputs.
"""
from typing import Type, TypeVar
from pydantic import BaseModel
import openai
from openai import OpenAI

from ai.providers.base import LLMProvider

T = TypeVar('T', bound=BaseModel)

class OpenAIProviderError(Exception):
    """
    Raised when the OpenAI provider fails during invoke or schema validation.
    """
    pass

class OpenAIProvider(LLMProvider):
    """
    OpenAI provider client wrapper that uses Pydantic structured outputs.
    """
    def __init__(self, model_id: str, config: dict):
        """
        Initialize the OpenAI client with model_id and config settings.
        
        Optional configurations like api_key, base_url, timeout, and max_retries 
        are passed directly to the OpenAI client.
        """
        super().__init__(model_id, config)
        
        client_kwargs = {}
        if "api_key" in config:
            client_kwargs["api_key"] = config["api_key"]
        if "base_url" in config:
            client_kwargs["base_url"] = config["base_url"]
        if "timeout" in config:
            client_kwargs["timeout"] = config["timeout"]
        if "max_retries" in config:
            client_kwargs["max_retries"] = config["max_retries"]
            
        try:
            self.client = OpenAI(**client_kwargs)
        except Exception as e:
            raise OpenAIProviderError(f"Failed to initialize OpenAI client: {e}") from e

    def invoke(self, prompt: str, schema: Type[T]) -> T:
        """
        Sends a compiled prompt text string to the OpenAI chat completions endpoint
        and returns a parsed schema contract response.
        """
        if not issubclass(schema, BaseModel):
            raise TypeError("schema must be a subclass of pydantic.BaseModel.")
            
        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model_id,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format=schema,
            )
            
            choice = completion.choices[0]
            
            # Handle refusals if safety triggers or constraints prevent structured outputs
            refusal = getattr(choice.message, "refusal", None)
            if refusal:
                raise OpenAIProviderError(f"OpenAI provider refusal occurred: {refusal}")
                
            parsed = choice.message.parsed
            if parsed is None:
                raise OpenAIProviderError("OpenAI provider returned empty parsed completion response.")
                
            return parsed
            
        except Exception as e:
            # Re-raise any OpenAIProviderError directly
            if isinstance(e, OpenAIProviderError):
                raise
            raise OpenAIProviderError(f"OpenAI provider invocation failed: {e}") from e
