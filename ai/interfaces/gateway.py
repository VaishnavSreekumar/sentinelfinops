"""
Abstract AIGateway interface definition.
"""
from abc import ABC, abstractmethod

class AIGatewayInterface(ABC):
    """
    Contract defining the AI Gateway transaction boundaries.
    """
    @abstractmethod
    def execute_reasoning(self, context, prompt_name: str, prompt_version: str, response_model):
        """
        Triggers optimization analysis on the target resource.
        """
        pass
