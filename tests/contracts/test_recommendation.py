"""
Unit tests for Recommendation contracts.
"""
import unittest
from uuid import UUID, uuid4
from pydantic import ValidationError
from ai.contracts.recommendation import RecommendationV1, RecommendationV2
from ai.contracts.enums import RecommendedAction

class TestRecommendation(unittest.TestCase):
    def setUp(self):
        self.valid_v1_data = {
            "recommendation_id": uuid4(),
            "model": "claude-3-5-sonnet",
            "prompt_version": "1.0.0",
            "resource_id": "i-09ab82910fa",
            "recommended_action": RecommendedAction.STOP_INSTANCE,
            "reasoning": "Underutilized compute instance.",
            "confidence_score": 0.95,
            "risk_assessment": {"level": "LOW", "remediation_risk": "None"},
            "projected_monthly_savings": 45.50,
            "explanation_steps": ["Check CPU metrics", "Attributed Owner", "Compare thresholds"],
            "citations": ["CPUUtil=1.2%"],
            "confidence_reason": "Consistent idle state over 7 days.",
            "assumptions": ["Not used for off-peak batch jobs"]
        }

        self.valid_v2_data = self.valid_v1_data.copy()
        self.valid_v2_data.update({
            "alternative_actions": ["RESIZE_INSTANCE"],
            "operational_impact": "Negligible impact on secondary queue processing."
        })

    def test_recommendation_v1_instantiation(self):
        rec = RecommendationV1(**self.valid_v1_data)
        self.assertEqual(rec.resource_id, "i-09ab82910fa")
        self.assertEqual(rec.schema_version, "1.0.0")
        self.assertIsInstance(rec.recommendation_id, UUID)
        self.assertEqual(rec.confidence_score, 0.95)

    def test_recommendation_v2_instantiation(self):
        rec = RecommendationV2(**self.valid_v2_data)
        self.assertEqual(rec.resource_id, "i-09ab82910fa")
        self.assertEqual(rec.schema_version, "2.0.0")
        self.assertEqual(rec.alternative_actions[0], "RESIZE_INSTANCE")
        self.assertEqual(rec.operational_impact, "Negligible impact on secondary queue processing.")

    def test_immutability(self):
        rec = RecommendationV1(**self.valid_v1_data)
        with self.assertRaises(ValidationError):
            rec.confidence_score = 0.99

    def test_invalid_confidence_score(self):
        # Confidence score must be >= 0.0 and <= 1.0
        data = self.valid_v1_data.copy()
        data["confidence_score"] = 1.5
        with self.assertRaises(ValidationError):
            RecommendationV1(**data)

    def test_invalid_savings_negative(self):
        # Savings must be >= 0.0
        data = self.valid_v1_data.copy()
        data["projected_monthly_savings"] = -10.0
        with self.assertRaises(ValidationError):
            RecommendationV1(**data)

    def test_schema_version_is_const(self):
        # Trying to instantiate V1 with schema_version="2.0.0" raises ValidationError
        data = self.valid_v1_data.copy()
        data["schema_version"] = "2.0.0"
        with self.assertRaises(ValidationError):
            RecommendationV1(**data)

    def test_forbid_extra_fields(self):
        data = self.valid_v1_data.copy()
        data["extra_property"] = "not-allowed"
        with self.assertRaises(ValidationError):
            RecommendationV1(**data)

if __name__ == "__main__":
    unittest.main()
