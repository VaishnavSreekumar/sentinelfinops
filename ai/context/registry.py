"""
MapperRegistry class definition.
Manages ContextMapper strategies using a plugin model.
"""
from typing import Dict
from ai.contracts.enums import ResourceType
from ai.context.base import ContextMapper

class MapperRegistry:
    """
    Registry container mapping resource types to their designated ContextMapper strategy.
    """
    def __init__(self):
        self._mappers: Dict[ResourceType, ContextMapper] = {}

    def register(self, mapper: ContextMapper) -> None:
        """
        Registers a mapper instance dynamically based on its supported type.
        """
        if not isinstance(mapper, ContextMapper):
            raise TypeError("Only instances of ContextMapper can be registered.")
        
        resource_type = mapper.supported_resource_type
        self._mappers[resource_type] = mapper

    def get_mapper(self, resource_type: ResourceType) -> ContextMapper:
        """
        Retrieves the mapper instance corresponding to the resource type.
        """
        mapper = self._mappers.get(resource_type)
        if not mapper:
            raise KeyError(f"No mapper registered for resource type: {resource_type}")
        return mapper
