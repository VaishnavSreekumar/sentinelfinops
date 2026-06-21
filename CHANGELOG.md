# Changelog

All notable changes to the SentinelFinOps project will be documented in this file.

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
