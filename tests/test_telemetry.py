"""
Unit tests for the AI Telemetry subsystem.
"""
import unittest
from uuid import uuid4
from pydantic import ValidationError

from ai.contracts.telemetry import TelemetryRecord
from ai.contracts.enums import PolicyValidationStatus
from ai.telemetry.tracker import TelemetryTracker

class TestTelemetryTracker(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = TelemetryTracker()

    def _create_record(
        self,
        resource_id: str = "vol-1234",
        validation_status: PolicyValidationStatus = PolicyValidationStatus.PASSED
    ) -> TelemetryRecord:
        return TelemetryRecord(
            request_id=uuid4(),
            execution_id=uuid4(),
            resource_id=resource_id,
            timestamp="2026-07-03T17:00:00Z",
            provider_name="openai",
            provider_model="gpt-4o",
            prompt_name="remediation_eval",
            prompt_version="1.0.0",
            cache_hit=False,
            latency_seconds=0.45,
            input_tokens=150,
            output_tokens=75,
            calculated_cost=0.0045,
            retry_attempts=0,
            validation_status=validation_status
        )

    def test_record_request(self) -> None:
        """Verify that record_request correctly appends a TelemetryRecord."""
        record = self._create_record()
        self.tracker.record_request(record)
        
        records = self.tracker.records
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].request_id, record.request_id)

    def test_record_response(self) -> None:
        """Verify that record_response correctly appends a TelemetryRecord."""
        record = self._create_record()
        self.tracker.record_response(record)
        
        records = self.tracker.records
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].request_id, record.request_id)

    def test_record_failure(self) -> None:
        """Verify that record_failure correctly appends a TelemetryRecord."""
        record = self._create_record(validation_status=PolicyValidationStatus.FAILED)
        self.tracker.record_failure(record)
        
        records = self.tracker.records
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].request_id, record.request_id)
        self.assertEqual(records[0].validation_status, PolicyValidationStatus.FAILED)

    def test_records_remain_ordered(self) -> None:
        """Verify that records are stored and retrieved in the order they were recorded."""
        record_1 = self._create_record(resource_id="res-1")
        record_2 = self._create_record(resource_id="res-2")
        record_3 = self._create_record(resource_id="res-3")

        self.tracker.record_request(record_1)
        self.tracker.record_response(record_2)
        self.tracker.record_failure(record_3)

        records = self.tracker.records
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].resource_id, "res-1")
        self.assertEqual(records[1].resource_id, "res-2")
        self.assertEqual(records[2].resource_id, "res-3")

    def test_records_are_immutable(self) -> None:
        """Verify that stored TelemetryRecord objects cannot be mutated."""
        record = self._create_record()
        self.tracker.record_request(record)
        
        stored_record = self.tracker.records[0]
        # Pydantic models with frozen=True raise ValidationError or TypeError on mutation
        with self.assertRaises((ValidationError, TypeError)):
            # Attempting to assign to a field of a frozen model raises an error
            stored_record.latency_seconds = 9.99  # type: ignore

    def test_defensive_copying(self) -> None:
        """Verify that retrieving records returns a copy, preventing list mutation."""
        record = self._create_record()
        self.tracker.record_request(record)

        # Retrieve records via property
        records_prop = self.tracker.records
        self.assertEqual(len(records_prop), 1)

        # Mutate the returned list
        records_prop.append(self._create_record())
        
        # Verify tracker's internal list remains unchanged
        self.assertEqual(len(self.tracker.records), 1)

        # Retrieve records via get_records() method
        records_meth = self.tracker.get_records()
        self.assertEqual(len(records_meth), 1)

        # Mutate the returned list
        records_meth.append(self._create_record())

        # Verify tracker's internal list remains unchanged
        self.assertEqual(len(self.tracker.records), 1)

    def test_passive_exception_safety(self) -> None:
        """Verify that telemetry calls do not raise exceptions if invalid data is passed."""
        # 1. Pass None instead of TelemetryRecord
        try:
            self.tracker.record_request(None)  # type: ignore
            self.tracker.record_response(None)  # type: ignore
            self.tracker.record_failure(None)  # type: ignore
        except Exception as e:
            self.fail(f"Telemetry tracker raised an exception on None input: {e}")

        # 2. Pass random string/object
        try:
            self.tracker.record_request("invalid-type")  # type: ignore
            self.tracker.record_response(12345)  # type: ignore
            self.tracker.record_failure({"some": "dict"})  # type: ignore
        except Exception as e:
            self.fail(f"Telemetry tracker raised an exception on invalid types: {e}")

        # Verify no invalid records were stored
        self.assertEqual(len(self.tracker.records), 0)
