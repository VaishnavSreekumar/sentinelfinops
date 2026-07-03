"""
TagNormalizer utility class.
Converts Cloud provider key-value lists into flat dictionaries.
"""
from typing import List, Dict, Union, Any

class TagNormalizer:
    """
    Utility helper to map list-of-dicts style tags list into flat key-value pairs dicts.
    """
    @staticmethod
    def to_flat_dict(tags: Union[List[Dict[str, Any]], Dict[str, str], None]) -> Dict[str, str]:
        """
        Transforms tag metadata formats into standard flat dictionaries.
        """
        if not tags:
            return {}
        if isinstance(tags, dict):
            return {str(k): str(v) for k, v in tags.items()}
        
        flat = {}
        if isinstance(tags, list):
            for item in tags:
                if isinstance(item, dict) and "Key" in item and "Value" in item:
                    flat[item["Key"]] = item["Value"]
        return flat
