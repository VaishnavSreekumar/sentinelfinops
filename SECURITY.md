# Security Policy

We take the security of our infrastructure management and FinOps tools seriously. If you believe you have found a security vulnerability in SentinelFinOps, please read below to report it.

## Supported Versions

Only the latest major version receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 4.5.x   | :white_check_mark: |
| 4.0.x   | :x:                |
| < 4.0   | :x:                |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please report security vulnerabilities by emailing the maintainers directly or utilizing GitHub's private vulnerability reporting feature.

Please include:
- A detailed description of the vulnerability.
- Steps to reproduce the issue (including any exploit scripts or proof of concept code).
- Potential impact or risk assessment.

We aim to acknowledge your report within 48 hours and provide a remediation timeline within 7 days.

## Security Model & Principles

SentinelFinOps operates inside your AWS environment and handles critical resource-management actions. To ensure security, the platform enforces:

1. **Least-Privilege Execution Roles**: Cross-account role assumptions (`SentinelFinOpsExecutionRole`) are strictly configured with read-only permissions except for targeted remediation actions (like EC2 stop, volume deletion, snapshot creation).
2. **Local Credential Sandboxing**: Secrets are stored only in environment variables or within `config/settings.yaml` (which is gitignored). They are never hardcoded or printed to stdout.
3. **No Automated Rollouts without Dry Run Option**: All scanning and remediation actions support global `--dry-run` safety parameters.
4. **Organizations Partitioning**: Member account scanning requires explicit STS assumption of roles. If role assumption fails, it logs the failure but continues scanning other accounts without failing the overall execution.
5. **No Direct Webhook Ingress**: The system communicates outgoing notifications to Slack via a one-way webhook endpoint and does not listen for incoming external webhook calls unless gated by API Gateway authentication.
