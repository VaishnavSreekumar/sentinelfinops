# Changelog

All notable changes to the SentinelFinOps project will be documented in this file.

## [v5.0.0] - 2026-07-04 (Cognitive Reasoning & Governance Firewall Integration)

This release evolves the platform from a heuristic scanner into an AI-driven, policy-gated cloud optimization suite. Cognitive AI optimization recommendations are dynamically generated, structured under safe canonical contracts, filtered by a compliance policy firewall, and presented via rich ChatOps interfaces.

### Added
- **Phase 1 (AI Contracts)**: Created Pydantic models for resource mapping contexts, model recommendations (`RecommendationV1`), policy validations, telemetry metrics, and enum properties.
- **Phase 2 (Context Mapping)**: Implemented `ContextMapper` registry featuring normalized mappings for `EC2Mapper` and `EBSMapper` to map raw boto3 results to type-safe inputs.
- **Phase 3 (Provider Abstraction)**: Designed the swappable `LLMProvider` interface to isolate the platform from external model clients.
- **Phase 4 (OpenAI Provider)**: Integrated OpenAI provider Client supporting structured output schema parsing, token counting, and custom API billing configurations.
- **Phase 5 (Prompt Registry)**: Implemented a filesystem-backed, version-controlled `PromptRegistry` under `config/prompts/` supporting semantic version sorting and discovery.
- **Phase 6 (AI Gateway)**: Created `AIGateway` to coordinate system context serialization, prompt retrieval, model execution, cost reporting, and caching.
- **Phase 7 (Schema Validator)**: Built a strict `SchemaValidator` to validate recommendation payloads against type definitions.
- **Phase 8 (Telemetry Subsystem)**: Created a passive event tracker (`TelemetryTracker`) logging request details, latency, and tokens with defensive copy protections.
- **Phase 9 (Policy Engine)**: Implemented a deterministic governance firewall (`PolicyEngine`) to evaluate AI proposals against compliance rules, enforcing fail-closed guardrails on any rule crashes.
- **Phase 10 (Slack AI presenter)**: Enhanced the Slack notifications handler to dynamically compile cost, savings, reasoning, and policy results without breaking legacy alerts.
- **Phase 11 (Runtime Integration)**: Created `AIRuntime` composition root and factory (`create_ai_runtime()`) and wired them into the EC2 and EBS scanner loops in `run_scan.py` with dynamic account details and fail-safe exceptions handling.
- **Phase 12 (AI Evaluation Framework)**: Implemented an offline developer validation suite (`Evaluator`, `EvaluationCase`, and `EvaluationResult`) to run sequential verification cases using mock providers.

---

## [v4.5] - 2026-06-22 (Enterprise Deployment & Production Readiness)

### Added
- Centralized configuration parsing via industry-standard `PyYAML`.
- Config validation enforcing `config_version: 1` check.
- Single global version file `version.py` as source of truth.
- Exhaustive validation engine via `python main.py validate` checking IAM, Organizations, DynamoDB, Lambda, EventBridge, and Slack connectivity.
- Global `--dry-run` override support via CLI flag.
- Detailed architecture diagrams stored as SVGs under `docs/images/` and documented in `ARCHITECTURE.md`.
- Open source assets: `LICENSE` (Apache 2.0), `CONTRIBUTING.md`, and `SECURITY.md`.
- Badges and Quick Start instructions inside `README.md`.
- CI/CD security scanning using `bandit` (Python) and `tfsec` (Terraform) in `.github/workflows/ci.yml`.
- Release packing automation producing zip packages and `SHA256SUMS.txt` in `.github/workflows/release.yml`.

### Changed
- Replaced the custom YAML parser with `PyYAML`'s `safe_load()`.
- Changed Slack check in installer validation to do non-pinging connectivity check rather than posting real webhook messages.

### Fixed
- Fixed notification import bug where `notifier.py` did not correctly map `SLACK_WEBHOOK_URL` to `WEBHOOK_URL`.

---

## [v4.0] - 2026-06-21 (Multi-Account & Production Safeguards)

### Added
- AWS Organizations member account scanning and cross-account role assumptions.
- Regional scanning support and configuration region allowlist/denylist.
- Remediation Dry Run mode and tag-based exemptions (`SentinelFinOps=Ignore`).
- Maintenance window constraints checking for remediation.
- STS session reuse cache to minimize API throttling and speed up large organizational scans.
- STS AssumeRole backoff retry logic.
- DynamoDB lock expiration (deadlock protection) after 15 minutes.
- Management account safety guard disabling remediation on the tool deployment account itself.

---

## [v3.0] - 2026-06-20 (Persistence & Notifications)

### Added
- Slack notifications integration for EC2 and EBS findings.
- Persistent Snooze management using DynamoDB.
- Alert state tracking to prevent duplicate notification spam.
- Automated EBS remediation backups (snapshots/AMIs) prior to stopping/deleting.

---

## [v2.5] - 2026-06-19 (Savings Calculations & Static Estimates)

### Added
- Multi-dimensional savings estimates using AWS Pricing API and static region cost estimation tables.
- Cost Explorer metric validation queries.
- HTML and console historical savings reporting.

---

## [v2.0] - 2026-06-18 (Optimization Scanners)

### Added
- EBS scanner to discover unattached, orphaned volumes.
- CloudWatch metrics queries to track average CPU usage.
- Idle engine heuristics detecting idle instances (CPU < 5%).

---

## [v1.x] - 2026-06-10 (Initial Release)

### Added
- Basic Single-Account EC2 scanner.
- Initial Terraform deployment scripts.
- CLI script to trigger local scans.
