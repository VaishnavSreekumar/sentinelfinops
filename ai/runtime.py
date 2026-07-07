"""
AI Runtime orchestrator (Composition Root).
Wires together the AI pipeline components.
"""
import os
from datetime import datetime
from typing import Tuple, Optional

# Import configuration loader
from config_loader import load_config

# Import AI pipeline components
from ai.contracts.scan_context import ScanContext
from ai.contracts.resource_context import ResourceContextV1
from ai.contracts.recommendation import RecommendationV1
from ai.contracts.policy_result import PolicyValidationResult
from ai.contracts.telemetry import TelemetryRecord
from ai.contracts.enums import PolicyValidationStatus, RiskLevel

from ai.context.registry import MapperRegistry
from ai.context.ec2_mapper import EC2Mapper
from ai.context.ebs_mapper import EBSMapper
from ai.context_builder import ContextBuilder

from ai.providers.openai import OpenAIProvider
from ai.prompts.registry import PromptRegistry
from ai.gateway import AIGateway
from ai.schema_validator import SchemaValidator

from policy.engine import PolicyEngine
from policy.rules.production_guard import ProductionGuardRule
from ai.telemetry.tracker import TelemetryTracker

class AIRuntime:
    """
    Orchestration class that executes the AI workflow for a resource context.
    Receives all required dependencies via constructor dependency injection.
    """
    def __init__(
        self,
        context_builder: ContextBuilder,
        gateway: AIGateway,
        schema_validator: SchemaValidator,
        policy_engine: PolicyEngine,
        telemetry_tracker: TelemetryTracker,
        provider_name: str,
        model_id: str,
        prompt_version: str = "1.0.0"
    ) -> None:
        self.context_builder = context_builder
        self.gateway = gateway
        self.schema_validator = schema_validator
        self.policy_engine = policy_engine
        self.telemetry_tracker = telemetry_tracker
        self.provider_name = provider_name
        self.model_id = model_id
        self.prompt_version = prompt_version

    def process(
        self,
        scan_context: ScanContext
    ) -> Tuple[Optional[RecommendationV1], Optional[PolicyValidationResult]]:
        """
        Runs the ScanContext through the mapping and reasoning pipeline.
        Gracefully returns (None, None) on any errors to fallback to deterministic flow.
        """
        start_time = datetime.utcnow()
        recommendation_id = None

        try:
            # 1. Map scan details to resource context
            resource_context = self.context_builder.build_context(scan_context)

            # 2. Query reasoning gateway
            recommendation = self.gateway.execute_reasoning(
                context=resource_context,
                prompt_name="cost_optimizer",
                prompt_version=self.prompt_version
            )
            recommendation_id = recommendation.recommendation_id

            # 3. Validate against schema
            self.schema_validator.validate(recommendation)

            # 4. Evaluate against deterministic policy rules
            policy_result = self.policy_engine.evaluate(recommendation)

            # 5. Record final metadata to telemetry
            end_time = datetime.utcnow()
            latency = (end_time - start_time).total_seconds()

            telemetry_record = TelemetryRecord(
                request_id=recommendation.recommendation_id,
                execution_id=scan_context.execution_id,
                resource_id=scan_context.resource_id,
                timestamp=end_time.isoformat() + "Z",
                provider_name=self.provider_name,
                provider_model=self.model_id,
                prompt_name="cost_optimizer",
                prompt_version=self.prompt_version,
                cache_hit=False,
                latency_seconds=latency,
                input_tokens=100,  # approximate/mock token metrics
                output_tokens=50,
                calculated_cost=0.003,
                retry_attempts=0,
                validation_status=policy_result.status
            )

            self.telemetry_tracker.record_request(telemetry_record)
            if policy_result.status == PolicyValidationStatus.PASSED:
                self.telemetry_tracker.record_response(telemetry_record)
            else:
                self.telemetry_tracker.record_failure(telemetry_record)

            return recommendation, policy_result

        except Exception as e:
            # Output failure message matching repository logging conventions
            print(f"AI Pipeline failed for resource {scan_context.resource_id}: {e}")

            # Record failure state to telemetry best-effort
            try:
                end_time = datetime.utcnow()
                latency = (end_time - start_time).total_seconds()
                telemetry_record = TelemetryRecord(
                    request_id=recommendation_id or scan_context.execution_id,
                    execution_id=scan_context.execution_id,
                    resource_id=scan_context.resource_id,
                    timestamp=end_time.isoformat() + "Z",
                    provider_name=self.provider_name,
                    provider_model=self.model_id,
                    prompt_name="cost_optimizer",
                    prompt_version=self.prompt_version,
                    cache_hit=False,
                    latency_seconds=latency,
                    input_tokens=0,
                    output_tokens=0,
                    calculated_cost=0.0,
                    retry_attempts=0,
                    validation_status=PolicyValidationStatus.FAILED
                )
                self.telemetry_tracker.record_request(telemetry_record)
                self.telemetry_tracker.record_failure(telemetry_record)
            except Exception:
                pass

            return None, None

def create_ai_runtime(config: Optional[dict] = None) -> AIRuntime:
    """
    Composition Root factory function.
    Loads configurations, instantiates components, and wires dependencies into AIRuntime.
    """
    cfg = config or load_config()
    ai_cfg = cfg.get("ai", {})

    # Retrieve values cleanly from config with env overrides and safe defaults
    provider_name = ai_cfg.get("provider", os.getenv("OPENAI_PROVIDER", os.getenv("AI_PROVIDER", "openai")))
    model_id = ai_cfg.get("model_id", os.getenv("AI_MODEL_ID", "gpt-4o"))
    api_key = ai_cfg.get("api_key", os.getenv("OPENAI_API_KEY", ""))

    # Locate prompts directory in config folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_prompts_dir = os.path.join(base_dir, "config", "prompts")
    prompts_dir = ai_cfg.get("prompts_dir", os.getenv("AI_PROMPTS_DIR", default_prompts_dir))

    # 1. Build context mapper dependencies
    mapper_registry = MapperRegistry()
    mapper_registry.register(EC2Mapper())
    mapper_registry.register(EBSMapper())
    context_builder = ContextBuilder(mapper_registry)

    # 2. Build Provider
    if provider_name.lower() == "mock":
        from ai.providers.mock_provider import MockProvider
        provider = MockProvider(model_id=model_id, config=ai_cfg)
        print("AI Provider: MockProvider")
    else:
        provider = OpenAIProvider(
            model_id=model_id,
            config={"api_key": api_key, **ai_cfg}
        )
        print("AI Provider: OpenAIProvider")

    # 3. Build prompt registry
    prompt_registry = PromptRegistry(prompts_dir)
    prompt_version = prompt_registry.get_latest_version("cost_optimizer")

    # 4. Build gateway, validator, policy engine, and telemetry tracker
    gateway = AIGateway(provider=provider, prompt_registry=prompt_registry)
    schema_validator = SchemaValidator()
    policy_engine = PolicyEngine(rules=[ProductionGuardRule(cfg)])
    telemetry_tracker = TelemetryTracker()

    return AIRuntime(
        context_builder=context_builder,
        gateway=gateway,
        schema_validator=schema_validator,
        policy_engine=policy_engine,
        telemetry_tracker=telemetry_tracker,
        provider_name=provider_name,
        model_id=model_id,
        prompt_version=prompt_version
    )
