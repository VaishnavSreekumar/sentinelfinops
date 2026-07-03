"""
Unit tests for PolicyValidationResult contracts.
"""
import unittest
from pydantic import ValidationError
from ai.contracts.policy_result import PolicyValidationResult
from ai.contracts.enums import PolicyValidationStatus

class TestPolicy(unittest.TestCase):
    def setUp(self):
        self.valid_data = {
            "status": PolicyValidationStatus.FAILED,
            "rule_name": "ProductionGuard",
            "severity": "CRITICAL",
            "violations": ["Confidence score 0.90 below 0.98 production limit"],
            "passed_rules": ["TagCompliance"],
            "failed_rules": ["ProductionGuard"],
            "timestamp": "2026-07-03T12:00:00Z"
        }

    def test_instantiation_success(self):
        res = PolicyValidationResult(**self.valid_data)
        self.assertEqual(res.status, PolicyValidationStatus.FAILED)
        self.assertEqual(res.schema_version, "1.0.0")
        self.assertEqual(res.violations[0], "Confidence score 0.90 below 0.98 production limit")

    def test_instantiation_defaults(self):
        data = self.valid_data.copy()
        del data["violations"]
        res = PolicyValidationResult(**data)
        self.assertEqual(res.violations, [])

    def test_validation_invalid_status(self):
        data = self.valid_data.copy()
        data["status"] = "PASSED_WITH_WARNINGS"
        with self.assertRaises(ValidationError):
            PolicyValidationResult(**data)

    def test_immutability(self):
        res = PolicyValidationResult(**self.valid_data)
        with self.assertRaises(ValidationError):
            res.rule_name = "NewRuleName"

    def test_forbid_extra(self):
        data = self.valid_data.copy()
        data["unallowed_data"] = True
        with self.assertRaises(ValidationError):
            PolicyValidationResult(**data)

if __name__ == "__main__":
    unittest.main()
