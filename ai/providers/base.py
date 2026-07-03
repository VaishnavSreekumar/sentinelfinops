"""
Abstract base class definition for LLM client providers.
"""
from abc import ABC, abstractmethod
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class LLMProvider(ABC):
    """
    Base contract for all language model provider clients.
    """
    def __init__(self, model_id: str, config: dict):
        self.model_id = model_id
        self.config = config

    @abstractmethod
    def invoke(self, prompt: str, schema: Type[T]) -> T:
        """
        Sends a compiled prompt text string to the model client
        and returns a parsed schema contract response.
        """
        pass
