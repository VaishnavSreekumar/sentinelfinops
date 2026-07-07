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

def dereference_schema(schema: dict) -> dict:
    """
    Recursively replaces $ref definitions with their actual content to produce a flat schema compatible with Gemini.
    """
    defs = schema.get("$defs", {}) or schema.get("definitions", {})
    
    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node:
                ref_path = node["$ref"]
                ref_name = ref_path.split("/")[-1]
                if ref_name in defs:
                    return resolve(defs[ref_name])
            return {k: resolve(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    flat_schema = resolve(schema)
    flat_schema.pop("$defs", None)
    flat_schema.pop("definitions", None)
    return flat_schema

class GeminiProvider(LLMProvider):
    """
    Direct Google Gemini REST API client wrapper.
    """
    def __init__(self, model_id: str, config: dict):
        super().__init__(model_id, config)
        # Accept API key from custom configuration or general environment variables
        self.api_key = (
            config.get("api_key") 
            or os.getenv("OPENAI_API_KEY") 
            or os.getenv("GEMINI_API_KEY") 
            or os.getenv("GOOGLE_API_KEY")
        )
        if not self.api_key:
            raise GeminiProviderError("Gemini API key is missing. Please set OPENAI_API_KEY or GEMINI_API_KEY.")
            
        # Standardize Gemini model naming
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
        
        # Generate JSON schema and dereference it to avoid $ref errors in Gemini
        raw_schema = schema.model_json_schema()
        json_schema = dereference_schema(raw_schema)
        
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
