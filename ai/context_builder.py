"""
ContextBuilder implementation mapping ScanContext payloads to ResourceContextV1.
Routes context builds dynamically to resolved mappers.
"""
from ai.contracts.resource_context import ResourceContextV1
from ai.contracts.scan_context import ScanContext
from ai.context.registry import MapperRegistry

class ContextBuilder:
    """
    Orchestration manager that routes a ScanContext payload to the correct Mapper strategy.
    """
    def __init__(self, registry: MapperRegistry):
        self.registry = registry

    def build_context(self, scan_context: ScanContext) -> ResourceContextV1:
        """
        Uses the registry plugin system to resolve a strategy mapper and run it.
        """
        if not isinstance(scan_context, ScanContext):
            raise TypeError("scan_context must be an instance of ScanContext.")
            
        mapper = self.registry.get_mapper(scan_context.resource_type)
        return mapper.map(scan_context)
