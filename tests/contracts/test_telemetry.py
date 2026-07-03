"""
Unit tests for TelemetryRecord contracts.
"""
import unittest
from uuid import UUID, uuid4
from pydantic import ValidationError
from ai.contracts.telemetry import TelemetryRecord
from ai.contracts.enums import PolicyValidationStatus

class TestTelemetry(unittest.TestCase):
    def setUp(self):
        self.valid_data = {
            "request_id": uuid4(),
            "execution_id": uuid4(),
            "resource_id": "i-09ab82910fa",
            "timestamp": "2026-07-03T12:00:00Z",
            "provider_name": "bedrock",
            "provider_model": "anthropic.claude-3-5-sonnet",
            "prompt_name": "cost_opt",
            "prompt_version": "1.0.0",
            "cache_hit": False,
            "latency_seconds": 2.54,
            "input_tokens": 1050,
            "output_tokens": 240,
            "calculated_cost": 0.0053,
            "retry_attempts": 0,
            "validation_status": PolicyValidationStatus.PASSED
        }

    def test_instantiation_success(self):
        record = TelemetryRecord(**self.valid_data)
        self.assertEqual(record.resource_id, "i-09ab82910fa")
        self.assertEqual(record.schema_version, "1.0.0")
        self.assertIsInstance(record.request_id, UUID)
        self.assertIsInstance(record.execution_id, UUID)
        self.assertEqual(record.cache_hit, False)

    def test_validation_negative_tokens(self):
        data = self.valid_data.copy()
        data["input_tokens"] = -5
        with self.assertRaises(ValidationError):
            TelemetryRecord(**data)

    def test_validation_negative_latency(self):
        data = self.valid_data.copy()
        data["latency_seconds"] = -1.2
        with self.assertRaises(ValidationError):
            TelemetryRecord(**data)

    def test_validation_negative_cost(self):
        data = self.valid_data.copy()
        data["calculated_cost"] = -0.01
        with self.assertRaises(ValidationError):
            TelemetryRecord(**data)

    def test_immutability(self):
        record = TelemetryRecord(**self.valid_data)
        with self.assertRaises(ValidationError):
            record.latency_seconds = 10.0

    def test_forbid_extra(self):
        data = self.valid_data.copy()
        data["extra_data"] = 123
        with self.assertRaises(ValidationError):
            TelemetryRecord(**data)

if __name__ == "__main__":
    unittest.main()
