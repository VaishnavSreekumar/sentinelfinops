# SentinelFinOps Architecture Guide (v5.0)

This document provides a technical guide to the system design, components, interfaces, deployment patterns, and execution sequences of SentinelFinOps v5.0.

---

## 1. Overall System Architecture

SentinelFinOps is structured as a decoupled, multi-layered system separating AWS resource discovery, cognitive AI reasoning, deterministic policy enforcement, state management, and presenter alerting.

```mermaid
flowchart TD
    subgraph Scheduling["Scheduling & Invocation"]
        Scheduler["AWS EventBridge Scheduler"] -->|Hourly Trigger| Lambda["Lambda Scanner"]
    end

    subgraph Discovery["Discovery & Context Collection"]
        Lambda -->|AWS Organizations| MemberAcc["AWS Member Accounts"]
        Lambda -->|CloudWatch API| CW["CPU Metrics Collection"]
        Lambda -->|Cost APIs| Cost["Cost & Savings Estimation"]
        Lambda -->|CloudTrail API| CT["Owner Tag Tracing"]
    end

    subgraph Runtime["AIRuntime Composition Root"]
        ScanCtx["ScanContext Schema"] -->|Context Mapping| ContextBuilder["ContextBuilder"]
        ContextBuilder -->|Mapped JSON| AIGateway["AI Gateway Interceptor"]
        AIGateway -->|LLM Prompt Query| Provider["Provider Abstraction"]
        Provider -->|Raw Output| SchemaValidator["Schema Validator"]
        SchemaValidator -->|RecommendationV1| PolicyEngine["Policy Engine Firewall"]
        PolicyEngine -->|Validation Status| TelemetryTracker["Telemetry Tracker"]
    end

    subgraph Presenter["State & Presentation"]
        PolicyEngine -->|PolicyResult| Slack["Slack Presenter"]
        Slack -->|Enriched Slack Block Kit| UserChannel["Slack ChatOps Channel"]
    end

    subgraph DB["Database State"]
        Lambda -->|Snoozes & Alert States| DDB["DynamoDB Tables"]
    end
```

---

## 2. Component Architecture

### Component Diagram

The repository modules are partitioned into scanning, core logic, AI pipelines, policies, and storage:

```mermaid
flowchart TD
    main["main.py CLI"] --> RunScan["scanner/run_scan.py"]
    main --> HealthCheck["monitoring/healthcheck.py"]
    main --> Validator["validation/install_validator.py"]
    main --> Server["server.py Slack Callback"]

    RunScan --> AIRuntime["ai/runtime.py"]
    AIRuntime --> ContextBuilder["ai/context_builder.py"]
    AIRuntime --> AIGateway["ai/gateway.py"]
    AIRuntime --> SchemaValidator["ai/schema_validator.py"]
    AIRuntime --> PolicyEngine["policy/engine.py"]
    AIRuntime --> TelemetryTracker["ai/telemetry/tracker.py"]

    RunScan --> Notifier["notifications/notifier.py"]
    Server --> RemediationManager["storage/remediation_manager.py"]
    RemediationManager --> DDBLocks["storage/remediation_lock.py"]
```

---

## 3. AI Subsystem Architecture

The AI reasoning layer operates as a strict validation pipeline. Raw system context is mapped to immutable contracts, processed by swappable providers, checked by structural validators, and filtered by a policy engine firewall before alerting or executing.

```mermaid
flowchart LR
    ScanContext["ScanContext Raw AWS Data"] -->|1. ContextMapper| ResourceContext["ResourceContextV1 Normalized Contract"]
    ResourceContext -->|2. Gateway execute| Gateway["AI Gateway Prompting + LLM"]
    Gateway -->|3. SchemaValidator| Recommendation["RecommendationV1 Pydantic Schema"]
    Recommendation -->|4. PolicyEngine evaluate| PolicyResult["PolicyValidationResult Governance Firewall"]
```

---

## 4. Deployment Architecture

SentinelFinOps is deployed entirely as serverless AWS infrastructure using Terraform, enforcing least-privilege permissions and zero permanent servers.

```mermaid
flowchart TD
    subgraph Management["AWS Management Account"]
        EventBridge["AWS EventBridge Cron Rule"] -->|Hourly Target| LambdaScan["Lambda: sentinelfinops-scanner"]
        FlaskServer["Flask Server server.py"] -->|Receives Actions| LambdaScan
        LambdaScan -->|Read/Write State| DDB_Snooze[("sentinelfinops-snoozes")]
        LambdaScan -->|Read/Write Alerts| DDB_AlertState[("sentinelfinops-alert-state")]
        LambdaScan -->|Write Audit Logs| DDB_Audit[("sentinelfinops-audit")]
        LambdaScan -->|Distributed Locks| DDB_Locks[("sentinelfinops-remediation-locks")]
    end

    subgraph Members["AWS Member Accounts"]
        LambdaScan -->|STS AssumeRole| TargetRole["SentinelFinOpsExecutionRole"]
        TargetRole -->|Metadata Scan| EC2["EC2 Instances"]
        TargetRole -->|Metadata Scan| EBS["EBS Volumes"]
    end
```

---

## 5. Runtime Sequence Diagram

The following sequence details how a scheduled run is executed, demonstrating how AI execution is optional and falls back gracefully on any pipeline failures:

```mermaid
sequenceDiagram
    autonumber
    participant Event as EventBridge
    participant Scanner as run_scan.py
    participant STS as AWS STS
    participant AIRuntime as AIRuntime (ai/runtime.py)
    participant Slack as Notifier (Slack)

    Event->>Scanner: Trigger Scheduled Scan
    Scanner->>STS: Assume Account Scanning Roles
    STS-->>Scanner: Session Credentials

    loop For Each Discovered Resource
        Scanner->>Scanner: Retrieve Heuristics (CPU, Cost)
        alt Resource is Active/Healthy
            Scanner->>Scanner: Clear existing alerts
        else Resource is Idle (Alert NEW)
            Scanner->>AIRuntime: process(ScanContext)
            alt AI Succeeds
                AIRuntime-->>Scanner: (RecommendationV1, PolicyResult)
            else AI Fails / Exception Raised
                AIRuntime-->>Scanner: (None, None)
            end
            Scanner->>Slack: send_alert(recommendation, policy_result)
        end
    end
```

---

## 6. Context Mapping Architecture

Raw discovery inputs are transformed into type-safe, versioned schemas by resource mappers registered inside a MapperRegistry.

```mermaid
classDiagram
    class ScanContext {
        +str resource_id
        +ResourceType resource_type
        +dict raw_resource
        +MetricsSummary metrics
        +CostSummary cost_summary
        +OwnerInfo owner_info
        +HistorySummary history_summary
        +str account_id
        +str region
    }

    class ContextMapper {
        +supported_resource_type : ResourceType
        +map(ScanContext) ResourceContextV1
    }

    class EC2Mapper {
        +map(ScanContext) ResourceContextV1
    }

    class EBSMapper {
        +map(ScanContext) ResourceContextV1
    }

    class MapperRegistry {
        +register(ContextMapper)
        +get_mapper(ResourceType) ContextMapper
    }

    class ContextBuilder {
        +build_context(ScanContext) ResourceContextV1
    }

    ScanContext --> ContextBuilder
    ContextBuilder --> MapperRegistry
    MapperRegistry --> ContextMapper
    ContextMapper <|-- EC2Mapper
    ContextMapper <|-- EBSMapper
```

---

## 7. Provider Abstraction

The system interacts with language models through the `LLMProvider` contract, isolating the codebase from changing API clients.

```mermaid
classDiagram
    class LLMProvider {
        +model_id : str
        +generate(system_prompt, user_prompt, response_schema)
    }

    class OpenAIProvider {
        +client : OpenAI
        +generate(system_prompt, user_prompt, response_schema)
    }

    class MockProvider {
        +responses : list
        +generate(system_prompt, user_prompt, response_schema)
    }

    LLMProvider <|-- OpenAIProvider
    LLMProvider <|-- MockProvider
```

---

## 8. Policy Validation Flow

The Policy Engine acts as a static compliance firewall, evaluating recommendations against deterministic rules. If any rule crashes, it fails closed immediately to protect target infrastructure.

```mermaid
flowchart TD
    Rec["RecommendationV1 Input"] --> Engine["PolicyEngine evaluate"]
    Engine --> Rule1["Rule 1: ProductionGuard"]
    Engine --> Rule2["Rule 2: ExemptionCheck"]

    Rule1 --> R1_Ok["OK (No Violations)"]
    Rule1 --> R1_Fail["Violation String"]
    Rule1 --> R1_Crash["Exception Captured"]

    R1_Ok --> Aggregator["Aggregator"]
    R1_Fail --> Aggregator
    R1_Crash --> Aggregator
    
    Aggregator --> Decision{"Any Violations or Crashes?"}
    
    Decision -->|Yes| ResultFail["PolicyValidationResult (Blocked)"]
    Decision -->|No| ResultPass["PolicyValidationResult (Allowed)"]
```

---

## 9. Telemetry Flow

The Telemetry Tracker records request lifecycles passively. It performs defensive copies of internal logs to prevent caller mutation.

```mermaid
flowchart TD
    Caller["AIRuntime / Evaluator"] -->|1. record_request| Tracker["TelemetryTracker"]
    Caller -->|2. record_response or record_failure| Tracker
    
    Tracker --> InternalList["_records : list[TelemetryRecord]"]
    
    UserQuery["get_records"] --> Tracker
    Tracker -->|Deep Copy/Defensive Copy| CopiedList["list[TelemetryRecord] (Read-Only Copy)"]
    CopiedList --> UserQuery
```

---

## 10. Evaluation Framework

Developers validation runs cases offline sequentially using a mock provider to verify contract compliance, policy results, and pipeline safety.

```mermaid
flowchart LR
    subgraph DevSuite["Developer Test Suite"]
        Case1["EvaluationCase 1"]
        Case2["EvaluationCase 2"]
    end

    subgraph Engine["Evaluator Engine"]
        Evaluator["Evaluator evaluator.py"]
        AIRuntime["AIRuntime process"]
    end

    Case1 -->|evaluate_all| Evaluator
    Case2 -->|evaluate_all| Evaluator
    Evaluator -->|Sequential Process| AIRuntime
    AIRuntime -->|Assert Policy & Actions| Evaluator
    Evaluator -->|Output Results| ResultList["list[EvaluationResult]"]
```

---

## 11. Repository Module Relationships

```mermaid
flowchart TD
    subgraph Subsystems
        Scanner["scanner/"]
        AI["ai/"]
        Policy["policy/"]
        Storage["storage/"]
        Notifications["notifications/"]
    end

    Scanner -->|Invokes| AI
    AI -->|Validates Against| Policy
    AI -->|Logs| Storage
    Scanner -->|Notifies| Notifications
    Notifications -->|Renders AI/Policy Details| Slack["Slack API"]
```

---

## 12. Design Principles & Patterns

1. **Single Source of Truth**: The platform ensures all components use defined configuration objects rather than hardcoded environment mappings.
2. **Fail-Safe Processing**: The AI pipeline resides in an isolated logical compartment. If any runtime exception is thrown (such as OpenAI timeout, Pydantic validation failure, or policy rule check crashes), the execution catches the crash and falls back immediately to legacy scanning heuristics.
3. **Immutability**: Contracts, recommendations, and execution contexts use Pydantic models configured as immutable (or frozen dataclasses) to prevent side-effect bugs.

---

## 13. Dependency Injection Strategy

SentinelFinOps uses constructor dependency injection throughout the AI runtime layer to isolate dependency building from execution logic:
- `AIRuntime` receives `ContextBuilder`, `AIGateway`, `SchemaValidator`, `PolicyEngine`, and `TelemetryTracker` via its constructor.
- Dependency instantiation resides in a single **Composition Root** factory function: `create_ai_runtime()`.
- This ensures `AIRuntime` can be tested easily by injecting mock objects, avoiding system registry state conflicts.

---

## 14. Extension Guide

### How to Add a New Provider
1. Inherit from `LLMProvider` in `ai/interfaces/provider.py`.
2. Implement the `generate` signature.
3. Register the new client implementation in the composition root `create_ai_runtime()` inside `ai/runtime.py`.

### How to Add a New Policy Rule
1. Inherit from `PolicyRule` in `policy/rules/base_rule.py`.
2. Implement `evaluate(self, recommendation: RecommendationV1, context: Any = None)`.
3. If validation fails, return a list of string violations. If it passes, return `True`.
4. Register the rule instance in the `create_ai_runtime` composition root's policy engine ruleset in `ai/runtime.py`.

### How to Add a New Prompt Template
1. Create a subdirectory under `config/prompts/` matching the prompt name.
2. Inside that directory, create a semantic version subdirectory (e.g. `1.1.0/`).
3. Add `system.txt` and `user.txt` templates. The `PromptRegistry` will automatically discover and sort the new templates.
