"""
Abstract PolicyRule template class.
"""
from abc import ABC, abstractmethod

class PolicyRule(ABC):
    """
    Abstract validation rule contract.
    """
    @abstractmethod
    def evaluate(self, recommendation, context):
        """
        Validates the recommendation against the target rules criteria.
        """
        pass
