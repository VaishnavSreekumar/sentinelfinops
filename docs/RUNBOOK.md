# SentinelFinOps Operations Runbook

This runbook describes the diagnostic and recovery procedures for common operational failures within the SentinelFinOps v4.5 platform.

---

## 1. Installation Validator Failures

If `python main.py validate` fails, inspect the following checkpoints based on the reported fails.

### STS Connection Failures (`[FAIL] STS Connection`)
* **Problem**: AWS CLI credentials are invalid, expired, or not present.
* **Resolution**:
  1. Check your active AWS profile: `aws sts get-caller-identity`.
  2. Verify that environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are correct.
  3. Ensure your local system time is synchronized; clock drift causes STS request rejections.

### Organizations Access Denied (`[FAIL] AWS Organizations`)
* **Problem**: The caller credentials reside in a member account rather than the organization management account, or the caller lacks `organizations:DescribeOrganization` and `organizations:ListAccounts` permissions.
* **Resolution**:
  1. Run the validator from the organization management account.
  2. Ensure the IAM policy attached to your user or deployment role allows `organizations:ListAccounts` and `organizations:DescribeOrganization`.

### DynamoDB Table Missing (`[FAIL] DynamoDB Table: sentinelfinops-*`)
* **Problem**: DynamoDB tables were not created or are in another region.
* **Resolution**:
  1. Verify the configured default region in `config/settings.yaml`.
  2. Run `terraform apply` to ensure the tables are correctly provisioned in your target region.

---

## 2. Cross-Account Assumption Failures

### Symptom: `Unable to assume role in account XXXXXXXXXXXX` in logs
* **Problem**: The member account has not been onboarded, or the execution role trust relationship is misconfigured.
* **Resolution**:
  1. Verify the `role_name` in `config/settings.yaml` matches the role name deployed in the member account (default is `SentinelFinOpsExecutionRole`).
  2. Run the onboarding bootstrap utility:
     ```bash
     python main.py bootstrap
     ```
  3. Inspect the trust relationship policy on `SentinelFinOpsExecutionRole` in the target member account. It must trust the management account ID.

---

## 3. Webhook/Slack Alerting Issues

### Symptom: Webhook pings succeed, but notifications are not received
* **Problem**: Slack webhook URL is invalid, or the channel specified does not accept the webhook payload.
* **Resolution**:
  1. Run `python main.py test-slack` to send a test alert.
  2. Verify that `slack.webhook_url` in `config/settings.yaml` is fully qualified and active.
  3. Ensure the Slack webhook app has been added to the target channel (e.g. `#general`).

---

## 4. Remediation Race Conditions & Deadlocks

### Symptom: Remediation fails with `Resource i-xxxxxxxx is locked`
* **Problem**: Another user triggered remediation, or a Lambda function crashed while holding a remediation lock.
* **Resolution**:
  1. Active locks expire automatically after 15 minutes.
  2. To manually break a lock, locate the item in the DynamoDB table `sentinelfinops-remediation-locks` where `resource_id` equals the blocked resource ID and delete the lock record.
