"""
AI Telemetry Tracker implementation.
Logs usage and metrics to databases and system events.
"""
from typing import List, Dict, Any, Optional
from ai.contracts.telemetry import TelemetryRecord

class TelemetryTracker:
    """
    In-memory observer that records execution metadata for AI requests.
    Exposes passive telemetry tracking methods that are guaranteed not to disrupt
    program flow or throw exceptions during normal recording operations.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self._records: List[TelemetryRecord] = []

    def record_request(self, record: TelemetryRecord) -> None:
        """
        Record a request event.
        """
        try:
            if not isinstance(record, TelemetryRecord):
                # Fail silently/gracefully as telemetry is best effort.
                return
            self._records.append(record)
        except Exception:
            # Telemetry is best-effort in this phase.
            return

    def record_response(self, record: TelemetryRecord) -> None:
        """
        Record a successful response event.
        """
        try:
            if not isinstance(record, TelemetryRecord):
                # Fail silently/gracefully as telemetry is best effort.
                return
            self._records.append(record)
        except Exception:
            # Telemetry is best-effort in this phase.
            return

    def record_failure(self, record: TelemetryRecord) -> None:
        """
        Record an execution failure event.
        """
        try:
            if not isinstance(record, TelemetryRecord):
                # Fail silently/gracefully as telemetry is best effort.
                return
            self._records.append(record)
        except Exception:
            # Telemetry is best-effort in this phase.
            return

    def get_records(self) -> List[TelemetryRecord]:
        """
        Retrieves a copy of the recorded TelemetryRecords in order.
        """
        return list(self._records)

    @property
    def records(self) -> List[TelemetryRecord]:
        """
        Property returning a copy of the recorded TelemetryRecords.
        """
        return self.get_records()

    def clear(self) -> None:
        """
        Clear the recorded telemetry events.
        """
        self._records.clear()
