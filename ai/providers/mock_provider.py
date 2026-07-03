"""
Mock LLM Provider implementation.
Generates dynamically populated schema instances without network operations.
"""
import uuid
import types
from enum import Enum
from typing import Type, TypeVar, Literal, Union, get_origin, get_args
from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from ai.providers.base import LLMProvider

T = TypeVar('T', bound=BaseModel)

class MockProvider(LLMProvider):
    """
    Mock client that dynamically returns populated schema objects based on Pydantic field specifications.
    """
    def invoke(self, prompt: str, schema: Type[T]) -> T:
        """
        Dynamically constructs dummy metadata based on the requested BaseModel schema annotations.
        """
        if not issubclass(schema, BaseModel):
            raise TypeError("schema must be a subclass of pydantic.BaseModel.")
            
        mock_data = {}
        for field_name, field_info in schema.model_fields.items():
            # Check for defaults or default factories first
            if field_info.default is not PydanticUndefined:
                mock_data[field_name] = field_info.default
                continue
            if field_info.default_factory is not None:
                mock_data[field_name] = field_info.default_factory()
                continue

            field_type = field_info.annotation
            origin = get_origin(field_type)
            
            # Resolve optional/union types to the first non-None argument
            if origin in (Union, getattr(types, "UnionType", None)):
                args = get_args(field_type)
                non_none_args = [arg for arg in args if arg is not type(None)]
                if non_none_args:
                    field_type = non_none_args[0]
                    origin = get_origin(field_type)

            # Handle Literals (e.g. Literal["1.0.0"])
            if origin is Literal:
                args = get_args(field_type)
                mock_data[field_name] = args[0] if args else None
            elif field_type is str:
                if field_name == "model" and self.model_id:
                    mock_data[field_name] = self.model_id
                else:
                    mock_data[field_name] = f"mock_{field_name}"
            elif field_type is float:
                mock_data[field_name] = 1.0
            elif field_type is int:
                mock_data[field_name] = 1
            elif field_type is bool:
                mock_data[field_name] = False
            elif field_type is uuid.UUID:
                mock_data[field_name] = uuid.uuid4()
            elif origin is list:
                mock_data[field_name] = []
            elif origin is dict:
                mock_data[field_name] = {}
            elif isinstance(field_type, type) and issubclass(field_type, Enum):
                # Retrieve the first Enum variant value
                mock_data[field_name] = list(field_type)[0]
            elif isinstance(field_type, type) and issubclass(field_type, BaseModel):
                # Recursively resolve nested Pydantic schemas
                mock_data[field_name] = self.invoke(prompt, field_type)
            else:
                mock_data[field_name] = None
                
        return schema(**mock_data)
