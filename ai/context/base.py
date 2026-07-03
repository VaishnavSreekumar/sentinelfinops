"""
Abstract base ContextMapper definition.
Enforces strategy parameters on resource conversion classes.
"""
from abc import ABC, abstractmethod
from ai.contracts.enums import ResourceType
from ai.contracts.resource_context import ResourceContextV1
from ai.contracts.scan_context import ScanContext

class ContextMapper(ABC):
    """
    Abstract Base Class for mapping cloud resource scan contexts to canonical contexts.
    """
    @property
    @abstractmethod
    def supported_resource_type(self) -> ResourceType:
        """
        The resource type enum this mapper handles.
        """
        pass

    @abstractmethod
    def map(self, scan_context: ScanContext) -> ResourceContextV1:
        """
        Translates a raw ScanContext object into standard ResourceContextV1.
        """
        pass
