"""
Google Gemini API LLM Provider implementation.
"""
import os
import json
import requests
from typing import Type, TypeVar, Any
from pydantic import BaseModel

from ai.providers.base import LLMProvider

T = TypeVar('T', bound=BaseModel)

class GeminiProviderError(Exception):
    """
    Raised when the Gemini provider fails during invoke or schema validation.
    """
    pass

def clean_and_dereference_schema(schema: dict) -> dict:
    """
    Cleans, dereferences, and sanitizes a Pydantic JSON schema to be 100% compliant with the Gemini API.
    Specifically:
      - Resolves and replaces '$ref' nodes inline.
      - Removes 'additionalProperties'.
      - Replaces Pydantic's 'const' (from Literals) with 'enum'.
      - Removes top-level '$defs' and 'definitions'.
    """
    defs = schema.get("$defs", {}) or schema.get("definitions", {})

    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node:
                ref_path = node["$ref"]
                ref_name = ref_path.split("/")[-1]
                if ref_name in defs:
                    return resolve(defs[ref_name])
            
            clean_node = {}
            for k, v in node.items():
                if k == "additionalProperties":
                    continue
                elif k == "const":
                    clean_node["enum"] = [v]
                elif k not in ("$defs", "definitions"):
                    clean_node[k] = resolve(v)
            return clean_node
        elif isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    flat_schema = resolve(schema)
    return flat_schema

class GeminiProvider(LLMProvider):
    """
    Direct Google Gemini REST API client wrapper.
    """
    def __init__(self, model_id: str, config: dict):
        super().__init__(model_id, config)
        self.api_key = (
            config.get("api_key") 
            or os.getenv("OPENAI_API_KEY") 
            or os.getenv("GEMINI_API_KEY") 
            or os.getenv("GOOGLE_API_KEY")
        )
        if not self.api_key:
            raise GeminiProviderError("Gemini API key is missing. Please set OPENAI_API_KEY or GEMINI_API_KEY.")
            
        self.api_model = model_id
        if not self.api_model.startswith("models/"):
            self.api_model = f"models/{self.api_model}"

    def invoke(self, prompt: str, schema: Type[T]) -> T:
        """
        Sends a compiled prompt text string to the Gemini REST API
        and returns a parsed schema contract response.
        """
        if not issubclass(schema, BaseModel):
            raise TypeError("schema must be a subclass of pydantic.BaseModel.")

        url = f"https://generativelanguage.googleapis.com/v1beta/{self.api_model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        # Generate and sanitize JSON schema
        raw_schema = schema.model_json_schema()
        json_schema = clean_and_dereference_schema(raw_schema)
        
        data = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": json_schema
            }
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code != 200:
                raise GeminiProviderError(f"Gemini API returned status code {response.status_code}: {response.text}")
                
            resp_json = response.json()
            candidates = resp_json.get("candidates", [])
            if not candidates:
                raise GeminiProviderError(f"Gemini API returned no candidates. Full response: {resp_json}")
                
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text")
            if not text:
                raise GeminiProviderError("Gemini API returned empty generation text.")
                
            try:
                parsed = schema.model_validate_json(text)
                return parsed
            except Exception as parse_err:
                raise GeminiProviderError(f"Failed to validate response against Pydantic schema: {parse_err}. Raw text: {text}")
                
        except Exception as e:
            if isinstance(e, GeminiProviderError):
                raise
            raise GeminiProviderError(f"Gemini provider invocation failed: {e}") from e
