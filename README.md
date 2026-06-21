# SentinelFinOps

[![Build Status](https://github.com/VaishnavSreekumar/sentinelfinops/actions/workflows/ci.yml/badge.svg)](https://github.com/VaishnavSreekumar/sentinelfinops/actions/workflows/ci.yml)
[![Security Scan](https://img.shields.io/badge/Security-Bandit%20%7C%20TFsec-blueviolet)](https://github.com/VaishnavSreekumar/sentinelfinops/SECURITY.md)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.13-blue)](https://www.python.org/)
[![Terraform Version](https://img.shields.io/badge/Terraform-%3E%3D%201.0-purple)](https://www.terraform.io/)

SentinelFinOps is an enterprise-grade cloud governance and FinOps automation platform that discovers idle, underutilized, and orphaned AWS EC2/EBS resources across multiple accounts and regions in an AWS Organization, alerts their owners via interactive Slack ChatOps, enforces guardrails, and manages auditable cost remediation.

---

## Quick Start

Get SentinelFinOps up and running in your environment in minutes:

```bash
# 1. Clone the repository
git clone https://github.com/VaishnavSreekumar/sentinelfinops.git
cd sentinelfinops

# 2. Setup a virtual environment & install pinned dependencies
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# 3. Create your live configuration file from template
cp config/settings.example.yaml config/settings.yaml

# 4. Initialize and apply Terraform to deploy foundations (DynamoDB, IAM, Lambda, Schedules)
cd terraform
terraform init
terraform apply
cd ..

# 5. Validate your installation parameters and IAM roles
python main.py validate

# 6. Check runtime health parameters and connectivity
python main.py health
```

---

## Core System Architecture

SentinelFinOps supports scheduled multi-account scans via cross-account IAM role assumption. Below are the key system architectures:

### 1. Runtime Scanning Architecture
EventBridge triggers the Lambda Scanner, which discovers AWS member accounts and assumes the execution role in each to analyze resources.
![Runtime Architecture](docs/images/runtime_architecture.svg)

### 2. Remediation Lifecycle Flow
Alerts are sent to Slack. Engineers click buttons to snooze, acknowledge, or trigger automated remediation with safety locks and backups.
![Remediation Flow](docs/images/remediation_flow.svg)

For complete architectural details, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Key Features

- **AWS Organizations Support**: Automatically discovers active member accounts and assumes pre-provisioned IAM execution roles.
- **Multi-Region & Allow/Deny Listing**: Scans all active AWS regions with custom allow/deny configuration parameters to exclude DR or GovCloud environments.
- **Stateful Remediation Locks**: Employs DynamoDB-based distributed locking with automatic 15-minute expirations to prevent race conditions during concurrent fixing actions.
- **Enterprise Configuration Ingestion**: Standardized YAML ingestion using PyYAML with validation rules checking `config_version: 1`.
- **Egress & Health Validation**: Built-in self-test tools to verify database tables, lambda environments, event rules, and connection check reachability of Slack without triggering duplicate notification spam.
- **Automatic Backups**: Creates EC2 AMIs and EBS Snapshots before performing any automated termination or stop action.

---

## Project Structure

```text
sentinelfinops/
 ├── .github/workflows/      # GitHub Action CI/CD pipelines (ci.yml & release.yml)
 ├── bootstrap/              # Automation tools for cross-account role boarding
 │    └── bootstrap_accounts.py
 ├── config/                 # YAML configuration settings & templates
 │    ├── settings.yaml      # User live configurations (gitignored)
 │    └── settings.example.yaml
 ├── docs/                   # Runbooks, documentation & architecture visuals
 │    ├── images/            # Exported SVG vector diagrams
 │    └── RUNBOOK.md         # Troubleshooting and incident response
 ├── engine/                 # Core analysis & heuristics engines
 │    ├── idle_engine.py
 │    └── cost_engine.py
 ├── monitoring/             # Health checking & CloudWatch metrics
 │    ├── healthcheck.py
 │    └── metrics.py
 ├── notifications/          # Alerting integration (Slack Block Kit)
 │    └── notifier.py
 ├── scanner/                # Boto3 client scans & CloudTrail owner tracing
 │    ├── ec2_scanner.py
 │    ├── ebs_scanner.py
 │    └── owner_detector.py
 ├── storage/                # Database state clients
 │    └── alert_state_manager.py
 ├── validation/             # Self-check validate suite
 │    └── install_validator.py
 ├── tests/                  # Unittest suite
 ├── terraform/              # Infrastructure code (IAM, DynamoDB, Lambda, EventBridge)
 ├── requirements.txt        # Pinned project dependencies
 ├── version.py              # Single source of truth version file
 ├── main.py                 # CLI entrypoint
 └── server.py               # Slack webhook callback server
```

---

## Open Source Compliance

Contributions are welcome! Please check [CONTRIBUTING.md](CONTRIBUTING.md) for style requirements, testing policies, and branch naming conventions. Refer to [SECURITY.md](SECURITY.md) to report vulnerabilities.

Licensed under the [Apache License, Version 2.0](LICENSE).
