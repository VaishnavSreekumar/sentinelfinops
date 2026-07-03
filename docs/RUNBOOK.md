# Operational Runbook - SentinelFinOps (v5.0)

This operational guide provides diagnostic procedures and troubleshooting steps for common infrastructure, configuration, and runtime errors in SentinelFinOps v5.0.

---

## 1. Installation Validator & Health Failures

If `python main.py validate` or `python main.py health` reports errors, inspect the recovery steps below:

### STS Connection Errors (`[FAIL] STS Connection / Identity`)
* **Cause**: Missing, invalid, or expired AWS profile credentials.
* **Troubleshooting**:
  1. Verify active AWS session CLI profile: `aws sts get-caller-identity`.
  2. Check local clock synchronization. Clock drift greater than 5 minutes causes AWS STS to reject signatures.
  3. Ensure that variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optional `AWS_SESSION_TOKEN` are set.

### Organization Access Denied (`[FAIL] AWS Organizations Permissions`)
* **Cause**: SentinelFinOps is run from a member account without access permissions, or target Organizations call is restricted.
* **Troubleshooting**:
  1. The platform scanning entry point must be run from the AWS Organization Management Account.
  2. Ensure the caller IAM user or execution profile has `organizations:ListAccounts` and `organizations:DescribeOrganization` permissions.

### Missing DynamoDB Tables (`[FAIL] DynamoDB Table: sentinelfinops-*`)
* **Cause**: DynamoDB state tables are not deployed in the target region.
* **Troubleshooting**:
  1. Verify region parameters in `config/settings.yaml` under `aws.default_region`.
  2. Run `terraform apply` inside `terraform/` to deploy the tables.

---

## 2. Configuration & AWS Permission Failures

### Cross-Account Role Assumption Failures
* **Symptom**: `Unable to assume role in account XXXXXXXXXXXX` logs during scanning.
* **Troubleshooting**:
  1. Check that the `SentinelFinOpsExecutionRole` exists in the target member account.
  2. Run the account onboarding script to create target roles:
     ```bash
     python main.py bootstrap
     ```
  3. Verify the role's trust relationship policy inside the member account. It must explicitly grant `sts:AssumeRole` permissions to the Management Account ID.

### Terraform Deployment Failures
* **Symptom**: `Error: lock table missing` or role deployment errors.
* **Troubleshooting**:
  1. Run `terraform init` to download provider plugins.
  2. If using a remote state backend, verify S3 bucket and DynamoDB locking table credentials.
  3. For local state, verify directory file write permissions.

---

## 3. Slack Webhook & presentation Failures

### Symptom: Webhook Test Succeeds, but Alerts Do Not Arrive
* **Cause**: Invalid Webhook channel routing or channel restrictions.
* **Troubleshooting**:
  1. Run `python main.py test-slack` to send a diagnostic alert.
  2. Verify the webhook URL in `config/settings.yaml` under `slack.webhook_url`.
  3. Ensure the Slack webhook App has been installed in the target workspace channel (e.g. `#general`).
  4. Inspect the HTTP status returned by the test command. An HTTP `403` indicates invalid channel routing, and `404` indicates a disabled webhook endpoint.

---

## 4. AI Pipeline & Model Failures

### Symptom: AI Pipeline Fails with `OpenAI connection error`
* **Cause**: Invalid or expired `OPENAI_API_KEY`, or network egress blocks to API endpoints.
* **Troubleshooting**:
  1. Verify the `OPENAI_API_KEY` environment variable is exported or set in `config/settings.yaml`.
  2. Test API egress by calling curl:
     ```bash
     curl -I https://api.openai.com/v1/chat/completions
     ```
  3. Check billing state on the OpenAI developer console. Account depletion causes immediate `429 Too Many Requests` API rejections.

### Symptom: AI Pipeline Fails with `PromptNotFoundError`
* **Cause**: Prompt template directory layout is invalid or templates are missing.
* **Troubleshooting**:
  1. Ensure the directory `config/prompts/` contains prompt folders (like `cost_optimizer/`).
  2. Verify that each prompt folder has a semver folder (like `1.0.0/`) containing both `system.txt` and `user.txt`.
  3. Verify file formatting. The user prompt template must use `{{ context_json }}` to inject the serialized resource context.

---

## 5. Remediation Locks & Race Conditions

### Symptom: Remediation Fails with `Resource i-xxxxxxxx is locked`
* **Cause**: Overlapping execution threads are trying to remediate the same resource, or a previous run crashed before releasing the lock.
* **Troubleshooting**:
  1. Active locks expire automatically after 15 minutes. Wait for the lease to expire and retry.
  2. To manually break a stuck lock, search for the resource ID in the DynamoDB table `sentinelfinops-remediation-locks` and delete the matching record.
