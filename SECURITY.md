# Security Policy - SentinelFinOps (v5.0)

We take the security of your AWS infrastructure and AI-assisted cloud governance seriously. This document outlines our security model, credentials handling, least-privilege configurations, and instructions for reporting vulnerabilities.

## Supported Versions

Only the latest major version receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 5.0.x   | :white_check_mark: |
| 4.x     | :x:                |
| < 4.0   | :x:                |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please report security vulnerabilities by emailing the maintainers directly or utilizing GitHub's private vulnerability reporting feature.

Please include:
- A detailed description of the vulnerability.
- Steps to reproduce the issue (including any exploit scripts or proof of concept code).
- Potential impact or risk assessment.

We aim to acknowledge your report within 48 hours and provide a remediation timeline within 7 days.

---

## 1. Secrets Management & API Keys

- **No Hardcoded Credentials**: The platform prohibits hardcoding API keys (such as `OPENAI_API_KEY`) or target webhook URLs.
- **Environment Isolation**: Secrets are loaded from the environment or target deployment settings using PyYAML safe loading of `config/settings.yaml` (which is gitignored).
- **Production Safety**: Mock keys or fallback credentials are never dynamically generated in production execution environments. If API keys are missing, the AI runtime fails closed and returns control to the deterministic heuristics scanner.

---

## 2. Least-Privilege IAM Framework

SentinelFinOps relies on a cross-account role assumption design. We enforce a separation between **read-only scanning** and **remediation write permissions** on the target `SentinelFinOpsExecutionRole` deployed in member accounts:

- **Metadata Scanners (Read-Only)**:
  - `ec2:DescribeInstances`
  - `ec2:DescribeVolumes`
  - `cloudwatch:GetMetricStatistics`
  - `organizations:ListAccounts` (Management account only)
- **Remediation Controllers (Write-Only)**:
  - `ec2:StopInstances` (EC2 Stop)
  - `ec2:DeleteVolume` (EBS delete)
  - `ec2:CreateSnapshot` (EBS backup)
  - `ec2:CreateImage` (EC2 AMI backup)
- **Trust Boundary**: Target execution roles must configure trust relationship policies allowing only the management account ID to assume the scanning profile.

---

## 3. AI Governance & Prompt Safety

- **Deterministic Compliance Firewall**: The AI Gateway generates optimization recommendations, but **never executes them directly**. The output `RecommendationV1` payload is intercepted by the `PolicyEngine` which enforces deterministic guardrails (such as production tag checks or safety overrides).
- **Fail-Closed Execution**: If any governance policy check crashes, the recommendation is rejected immediately, preventing unvalidated AI output from interacting with AWS resources.
- **Prompt Injection Defense**: The prompt registry is filesystem-backed under `config/prompts/` and is version-controlled. User inputs are serialized within structured JSON templates (`user.txt`) using the `{{ context_json }}` placeholder, separating system instructions from context variables to prevent command/prompt injection.

---

## 4. Remediation Safety Guardrails

- **Management Account Protection**: Automated remediation is blocked on resources residing in the AWS Organization Management Account.
- **Dry-Run Mode**: The platform supports a global `--dry-run` override configuration, allowing engineers to audit recommendations and policy outcomes in Slack without modifying AWS states.
