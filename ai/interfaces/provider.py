"""
Abstract LLMProvider interface definition.
"""
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    """
    Base contract for all language model provider clients.
    """
    @abstractmethod
    def invoke(self, system: str, user: str, schema):
        """
        Queries the model provider and parses responses to target schema models.
        """
        pass
