"""
Unit tests for the direct REST GeminiProvider implementation.
"""
import unittest
from unittest.mock import patch, MagicMock
from pydantic import BaseModel
from ai.providers.gemini import GeminiProvider, GeminiProviderError, clean_and_dereference_schema

class MockSchema(BaseModel):
    name: str
    value: int

class TestGeminiProvider(unittest.TestCase):
    def test_dereference_schema(self):
        """Assert that local definitions refs are resolved, additionalProperties are removed, and const maps to enum."""
        raw_schema = {
            "properties": {
                "val": {"$ref": "#/$defs/MyEnum"},
                "constant": {"const": "fixed_val"}
            },
            "additionalProperties": False,
            "$defs": {
                "MyEnum": {"type": "string", "enum": ["A", "B"]}
            }
        }
        flat = clean_and_dereference_schema(raw_schema)
        self.assertEqual(flat["properties"]["val"], {"type": "string", "enum": ["A", "B"]})
        self.assertEqual(flat["properties"]["constant"], {"enum": ["fixed_val"]})
        self.assertNotIn("additionalProperties", flat)
        self.assertNotIn("$defs", flat)

    @patch("requests.post")
    def test_invoke_success(self, mock_post):
        """Assert that a successful response from Google is correctly validated and parsed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": '{"name": "test_resource", "value": 42}'}
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = GeminiProvider(model_id="gemini-1.5-flash", config={"api_key": "test_key"})
        result = provider.invoke("Optimize this", MockSchema)
        
        self.assertEqual(result.name, "test_resource")
        self.assertEqual(result.value, 42)

    @patch("requests.post")
    def test_invoke_failure(self, mock_post):
        """Assert that an API failure triggers a GeminiProviderError."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response

        provider = GeminiProvider(model_id="gemini-1.5-flash", config={"api_key": "test_key"})
        with self.assertRaises(GeminiProviderError):
            provider.invoke("Optimize this", MockSchema)

if __name__ == "__main__":
    unittest.main()
