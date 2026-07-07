"""
Mock LLM Provider implementation.
Generates dynamically populated schema instances without network operations.
"""
import uuid
import json
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
    Extracts resource context details from the prompt payload to return realistic, deterministic Recommendations.
    """
    def invoke(self, prompt: str, schema: Type[T]) -> T:
        """
        Returns a deterministic recommendation if the schema matches RecommendationV1,
        falling back to dynamic field generation for test schemas.
        """
        if not issubclass(schema, BaseModel):
            raise TypeError("schema must be a subclass of pydantic.BaseModel.")
            
        from ai.contracts.recommendation import RecommendationV1
        from ai.contracts.enums import RecommendedAction

        # Check if we can return a deterministic realistic recommendation for RecommendationV1
        if issubclass(schema, RecommendationV1):
            resource_id = "mock_resource"
            resource_type = "EC2"
            cpu_usage = 0.5
            current_cost = 0.0
            
            if "Context:\n" in prompt:
                try:
                    context_str = prompt.split("Context:\n", 1)[1].strip()
                    context_data = json.loads(context_str)
                    resource_id = context_data.get("resource_id", "mock_resource")
                    
                    res_type_raw = context_data.get("resource_type", "EC2")
                    if isinstance(res_type_raw, str):
                        resource_type = res_type_raw
                    elif hasattr(res_type_raw, "value"):
                        resource_type = res_type_raw.value
                    else:
                        resource_type = str(res_type_raw)
                        
                    metrics = context_data.get("metrics_summary") or {}
                    if "cpu_mean_7_days" in metrics and metrics["cpu_mean_7_days"] is not None:
                        cpu_usage = float(metrics["cpu_mean_7_days"])
                    elif "cpu_max_7_days" in metrics and metrics["cpu_max_7_days"] is not None:
                        cpu_usage = float(metrics["cpu_max_7_days"])
                    
                    current_cost = float(metrics.get("current_cost") or metrics.get("projected_savings") or 0.0)
                except Exception:
                    pass
            
            # Deterministic UUID generation using namespace DNS
            rec_id = uuid.uuid5(uuid.NAMESPACE_DNS, resource_id)
            
            if resource_type == "EBS":
                savings = current_cost if current_cost > 0.0 else 4.0
                return schema(
                    recommendation_id=rec_id,
                    generated_at="2026-07-07T00:00:00Z",
                    model=self.model_id,
                    prompt_version="1.0.0",
                    resource_id=resource_id,
                    recommended_action=RecommendedAction.DELETE_VOLUME,
                    reasoning="Volume has not been attached within the observation window. Snapshot before deletion.",
                    confidence_score=0.95,
                    risk_assessment={"data_loss": "low"},
                    projected_monthly_savings=savings,
                    explanation_steps=["Identify unattached EBS volume", "Create backup snapshot", "Delete volume to stop charges"],
                    citations=["EBS volume state is available"],
                    confidence_reason="Volume has been unattached for 7+ days.",
                    assumptions=["No active application is configured to mount this volume", "A snapshot backup is sufficient for archival recovery"],
                    schema_version="1.0.0"
                )
            else: # EC2
                if cpu_usage < 1.0:
                    savings = current_cost if current_cost > 0.0 else 10.0
                    return schema(
                        recommendation_id=rec_id,
                        generated_at="2026-07-07T00:00:00Z",
                        model=self.model_id,
                        prompt_version="1.0.0",
                        resource_id=resource_id,
                        recommended_action=RecommendedAction.STOP_INSTANCE,
                        reasoning="CPU utilisation has remained below 1% for the configured observation window. No recent activity detected. Estimated monthly savings justify remediation. Create an AMI before termination. Notify owner.",
                        confidence_score=0.98,
                        risk_assessment={"service_disruption": "low"},
                        projected_monthly_savings=savings,
                        explanation_steps=["Verify CPU usage is idle (< 1.0%)", "Generate AMI backup of instance root volume", "Stop instance to prevent billing charges"],
                        citations=["CPU mean is under 1.0%"],
                        confidence_reason="Mean CPU utilization is flatlined at 1.0% or less.",
                        assumptions=["The instance is not a warm standby", "The owner can restart the instance if needed"],
                        schema_version="1.0.0"
                    )
                elif cpu_usage < 5.0:
                    savings = current_cost / 2.0 if current_cost > 0.0 else 5.0
                    return schema(
                        recommendation_id=rec_id,
                        generated_at="2026-07-07T00:00:00Z",
                        model=self.model_id,
                        prompt_version="1.0.0",
                        resource_id=resource_id,
                        recommended_action=RecommendedAction.RESIZE_INSTANCE,
                        reasoning="Average CPU utilisation remains consistently below threshold. Recommend moving to a smaller instance type.",
                        confidence_score=0.91,
                        risk_assessment={"service_disruption": "medium"},
                        projected_monthly_savings=savings,
                        explanation_steps=["Analyze CPU utilization over 7 days", "Compare current type to smaller sizes", "Recommend resizing to reduce cost"],
                        citations=["CPU mean is consistently under 5.0%"],
                        confidence_reason="Consistently low resource usage suggests overprovisioning.",
                        assumptions=["The workload does not have memory-intensive spikes", "A smaller instance type supports the required bandwidth"],
                        schema_version="1.0.0"
                    )
                else:
                    return schema(
                        recommendation_id=rec_id,
                        generated_at="2026-07-07T00:00:00Z",
                        model=self.model_id,
                        prompt_version="1.0.0",
                        resource_id=resource_id,
                        recommended_action=RecommendedAction.NO_ACTION,
                        reasoning="CPU utilization is active and within acceptable limits. No remediation action is required.",
                        confidence_score=0.90,
                        risk_assessment={"none": "none"},
                        projected_monthly_savings=0.0,
                        explanation_steps=["Analyze CPU utilization", "Confirm resource is active", "No action required"],
                        citations=["CPU utilization is above threshold"],
                        confidence_reason="Instance is actively processing workloads.",
                        assumptions=["Workload levels will continue at current rate"],
                        schema_version="1.0.0"
                    )

        # Fallback loop to dynamically generate fields for test schemas/other models
        mock_data = {}
        for field_name, field_info in schema.model_fields.items():
            if field_info.default is not PydanticUndefined:
                mock_data[field_name] = field_info.default
                continue
            if field_info.default_factory is not None:
                mock_data[field_name] = field_info.default_factory()
                continue

            field_type = field_info.annotation
            origin = get_origin(field_type)
            
            if origin in (Union, getattr(types, "UnionType", None)):
                args = get_args(field_type)
                non_none_args = [arg for arg in args if arg is not type(None)]
                if non_none_args:
                    field_type = non_none_args[0]
                    origin = get_origin(field_type)

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
                mock_data[field_name] = list(field_type)[0]
            elif isinstance(field_type, type) and issubclass(field_type, BaseModel):
                mock_data[field_name] = self.invoke(prompt, field_type)
            else:
                mock_data[field_name] = None
                
        return schema(**mock_data)
