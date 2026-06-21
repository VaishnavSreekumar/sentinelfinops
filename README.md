# SentinelFinOps

![Python](https://img.shields.io/badge/Python-3.13-blue)
![AWS](https://img.shields.io/badge/AWS-Cloud-orange)
![Terraform](https://img.shields.io/badge/Terraform-IaC-purple)
![Slack](https://img.shields.io/badge/Slack-ChatOps-green)

A cloud governance and FinOps automation platform that discovers underutilized AWS EC2 instances, estimates potential waste, identifies resource creators via CloudTrail, and drives remediation through interactive ChatOps (Slack) snooze and audit workflows.

---

### Above the Fold: Quick Context

#### 1. What is SentinelFinOps?
SentinelFinOps is an automated agentic engine designed to continuously monitor, analyze, and govern AWS resource spend by closing the feedback loop between idle cloud infrastructure, resource owners, and financial accountability.

#### 2. What problem does it solve?
It prevents unchecked cloud spending caused by forgotten/abandoned developer instances by shifting accountability to the resource creators without introducing intrusive or heavy dashboards.

#### 3. What technologies power it?
* **Backend**: Python, Boto3 (AWS SDK), Flask (Interactivity Webhook API).
* **AWS Services**: EC2, CloudWatch (CPU Metrics), CloudTrail (Creator Identity Tracking), IAM.
* **Infrastructure**: Terraform (Bootstrap foundations).
* **ChatOps & Storage**: Slack Webhooks & Block Kit, Local JSON State Storage.

#### 4. How is it different from a simple AWS monitoring script?
Unlike static monitoring scripts that merely output reports, SentinelFinOps:
* **Resolves resource ownership dynamically** by tracing creation events in CloudTrail.
* **Enables interactive remediation** directly inside team communication channels (Slack) via buttons.
* **Maintains state lifecycle** through robust, timezone-aware Snooze and Audit Log subsystems to ensure engineering teams are not spammed with duplicate alerts.

---

### Architecture Preview & Core Flow

```
   ┌─────────┐      ┌──────────────┐      ┌─────────────────┐      ┌─────────────┐
   │ AWS EC2 ├─────►│ CloudWatch   ├─────►│ CloudTrail      ├─────►│ Slack Alert │
   │ Scan    │      │ CPU Metrics  │      │ Owner Detection │      │ Event       │
   └─────────┘      └──────────────┘      └─────────────────┘      └──────┬──────┘
                                                                          │ (Button Click)
                                                                          ▼
                                                                ┌─────────┴─────────┐
                                                                │  Flask Webhook    │
                                                                └─┬───────────────┬─┘
                                                                  │               │
                                                                  ▼ (Snooze)      ▼ (Acknowledge)
                                                            ┌─────┴─────┐   ┌─────┴─────┐
                                                            │snoozes.json│   │audit_log.json
                                                            └───────────┘   └───────────┘
```

---

## Why SentinelFinOps Exists

Most organizations fail to manage cloud waste due to structural and social roadblocks in cloud operations (FinOps):

1. **Unknown Ownership**: An alert saying `i-077033ecaacb77270 is idle` is useless if nobody knows who launched it. SentinelFinOps queries AWS CloudTrail to find the exact IAM user or assumed role session that executed `RunInstances`.
2. **Alert Fatigue**: Flooding channels with daily reports leads to engineers ignoring them. SentinelFinOps implements a **Snooze** workflow, giving owners 24 hours of quiet time to review, while logging the suppression.
3. **Cost Accountability**: By estimating monthly waste based on specific instance types (e.g. `t2.micro`, `t3.small`) and highlighting potential savings, it translates abstract CPU metrics into real business dollar impact.
4. **Lack of Recognition for Savings**: FinOps teams struggle to prove impact. The **Audit Log** records every acknowledgment and snooze action, creating a transparent audit trail of active cost-containment engagement.

---

## Key Features & Business Value

| Feature | Technical Implementation | Business Value |
| :--- | :--- | :--- |
| **Active Resource Discovery** | Uses Boto3 `describe_instances` to dynamically scan active EC2 instances and retrieve metadata such as instance types and `Name` tags. | Prevents asset blindness and ensures a real-time registry of all active compute resources. |
| **Idle Detection Engine** | Queries CloudWatch for `CPUUtilization` averages over the past 1 hour. Classifies instances as idle if average CPU drops below `5.0%`. | Eliminates manual metric reporting, automatically isolating wasteful compute. |
| **Cost Estimation Engine** | Maps compute instance types to hourly rates and projects monthly costs and potential savings. | Empowers decision-makers with concrete monthly dollar figures rather than abstract load percentages. |
| **CloudTrail Owner Lookup** | Leverages `LookupEvents` filtered by resource ID to parse `userIdentity` and find the IAM creator (User or Assumed Role). | Solves the "orphan resource" problem by holding the exact creator accountable for the costs. |
| **Interactive Slack Alerts** | Pushes rich Block Kit notifications containing instance specifications, cost data, owner, and action buttons. | Meets engineers where they work (Slack), enabling zero-friction cost-containment workflows. |
| **Stateful Alert Snoozing** | Stores a timezone-aware ISO expiration timestamp in `snoozes.json`. Suppresses subsequent run alerts for 24 hours. | Protects developer focus by eliminating repetitive notifications for known issues. |
| **Remediation Audit Logging** | Appends structured action records (e.g. `acknowledged`) with UTC timestamps into `audit_log.json` upon interaction. | Establishes a verifiable history of cloud governance operations for compliance and reporting. |
| **Terraform Bootstrap** | Provisions the IAM User, required governance policy permissions, and an EventBridge rule placeholder. | Standardizes environment deployments via automated, version-controlled Infrastructure as Code. |

---

## Project Structure

```
sentinelfinops/
├── config/                  # Configuration directory (reserved for future deployment targets)
├── engine/                  # Core analysis logic
│   ├── cost_engine.py       # EC2 pricing calculation and monthly projections
│   └── idle_engine.py       # Metrics threshold evaluation rules
├── notifications/           # Alert delivery layer
│   └── notifier.py          # Slack Webhook client and Block Kit payload generator
├── scanner/                 # Cloud state metrics and logs retrieval
│   ├── cloudwatch_scanner.py# Queries CPU metrics from CloudWatch
│   ├── ec2_scanner.py       # Resolves EC2 instances and metadata tags
│   └── owner_detector.py    # Audits CloudTrail to identify resource creators
├── storage/                 # State management layer
│   ├── audit_log.json       # Audit trail of engineering actions
│   ├── audit_logger.py      # Appends action entries to the audit database
│   ├── snooze_manager.py    # Loads snoozes and determines active suppressions
│   └── snoozes.json         # Stores instance snooze expiration dates
├── terraform/               # Infrastructure as Code bootstrap
│   ├── main.tf              # Declares IAM roles/users, policies, and EventBridge rule
│   ├── outputs.tf           # Exports ARNs of bootstrap resources
│   └── variables.tf         # Declares environment configuration parameters
├── .ENV                     # Environment configuration variables (local development)
├── .gitignore               # Ensures secure configuration hygiene
├── main.py                  # CLI application entrypoint and main run-loop
├── requirements.txt         # Project python dependencies
├── server.py                # Flask webhook receiver for interactive Slack callbacks
└── test_slack.py            # Diagnostic utility for Slack messaging
```

---

## Demo Workflow

1. **EC2 Instance Becomes Idle**: A developer provisions a `t3.micro` instance named `sentinelfinops-test` (ID: `i-077033ecaacb77270`) and leaves it running unattended with CPU averaging 2.06%.
2. **Analysis Execution**: The `main.py` daemon is triggered. The **EC2 Scanner** pulls the metadata and Name tag, and the **CloudWatch Scanner** retrieves the CPU statistics.
3. **Cost Projection**: The **Cost Engine** estimates that this instance generates $8.35/month of waste.
4. **Creator Tracking**: The **Owner Detector** parses CloudTrail logs for the matching `RunInstances` event, identifying the owner as `sentinelfinops-dev`.
5. **Interactive Alerting**: A Slack Block Kit notification is fired to the engineering channel:
   * **Slack Alert Preview**:
     ```
     ⚠️ SentinelFinOps Alert
     Instance Name: sentinelfinops-test
     Instance ID: i-077033ecaacb77270
     Owner: sentinelfinops-dev
     CPU Usage: 2.06%
     Estimated Monthly Cost: $8.35
     Potential Savings: $8.35/month
     Recommendation: Review or Terminate
     [✅ Acknowledge] [⏰ Snooze]
     ```
6. **User Interaction**:
   * If the owner clicks **Acknowledge**: An HTTP POST callback is received by `server.py` which triggers `audit_logger.py` to record the acknowledgment in `audit_log.json`.
   * If the owner clicks **Snooze**: The callback registers a snooze in `snoozes.json` with an expiration set 24 hours in the future.
7. **Snooze Enforcement**: On subsequent run loops, `main.py` queries `snooze_manager.py` before executing alerts. Since the instance is snoozed, it prints `⏰ Alert suppressed (snoozed)` to the console and skips the Slack notification.

## Deployment Modes

SentinelFinOps supports two operation modes depending on your target environment:

### 1. Local CLI Mode
In this mode, the platform is executed as a command-line utility. The main application is run locally or on a cron schedule on a management server.
* **Command**: `python main.py`
* **Flow**: Scans EC2 and CloudWatch metrics locally, triggers Slack alerts, and relies on a locally running Flask callback API (`python server.py`) to process interactive button responses.

### 2. Automated AWS Mode
In this mode, the orchestrator runs completely serverless within AWS.
* **Infrastructure**: An EventBridge rule schedules a Lambda function (`lambda_function.py`) to execute every 1 hour.
* **Flow**: The Lambda function imports and executes the shared `run_scan()` function, and environment variables are used to securely pass configurations (such as `SLACK_WEBHOOK_URL`).

---

## Local Setup

### 1. Prerequisites
* **Python**: Python 3.13+ installed.
* **AWS CLI**: Installed and configured with permissions to query EC2, CloudWatch, and CloudTrail.
* **Slack WorkSpace**: Access to create a Slack app and retrieve a Webhook URL.
* **Ngrok**: Installed locally for webhook tunneling.

### 2. Install Dependencies
Initialize a virtual environment and install the required modules:
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure the Slack Application
1. Navigate to [Slack API Console](https://api.slack.com/apps) and select **Create New App**.
2. Enable **Incoming Webhooks** and generate a Webhook URL for your target channel.
3. Go to **Interactive Components**, toggle Interactivity to **On**, and save a placeholder request URL (e.g. `https://your-ngrok-subdomain.ngrok-free.app/slack/actions`).

### 4. Configure Environment Variables
Create a file named `.env` in the project root:
```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_KEY
AWS_DEFAULT_REGION=us-east-1
```

### 5. Start the Webhook Callback Server
Run the Flask API server locally to listen for Slack interactions:
```bash
.\venv\Scripts\activate
python server.py
```

### 6. Establish a Webhook Tunnel
Expose local port 5000 to the public web via Ngrok so Slack can deliver interactive button payloads:
```bash
ngrok http 5000
```
Update your Slack App's **Request URL** in the developer console with the public HTTPS URL generated by Ngrok.

---

## Terraform Provisioning

SentinelFinOps includes a minimal Terraform bootstrap configuration that provisions the required IAM permissions and scheduler frameworks.

### Setup and Deployment:
1. Navigate to the `terraform` directory:
   ```bash
   cd terraform
   ```
2. Initialize the backend and providers:
   ```bash
   terraform init
   ```
3. Validate the syntax of the configuration:
   ```bash
   terraform validate
   ```
4. View the execution plan to inspect the resources that will be provisioned:
   ```bash
   terraform plan
   ```

Resources provisioned by this plan:
* **IAM User** `sentinelfinops-dev`
* **IAM Policy** providing least-privilege permissions (`ec2:DescribeInstances`, `cloudwatch:GetMetricStatistics`, `cloudtrail:LookupEvents`)
* **EventBridge Rule** placeholder to trigger future scheduled execution of the daemon.

---

## Future Roadmap

1. **Monthly Savings Reports**: Automated generation of CSV/JSON savings reports delivered directly via email or Slack.
2. **Slack Message Updates**: Modify the interactive webhook response to dynamically update/replace the Slack message blocks upon clicking "Acknowledge" or "Snooze".
3. **Resource Remediation Workflows**: Adding automated opt-in termination or scheduling stop events for instances remaining idle after multiple snoozes.
4. **Automated Scheduling**: Deploying the execution loop to AWS Lambda, scheduled hourly by the EventBridge rule.

---


* **Distributed State Management**: Designing lightweight state storage parsing timezone-aware date comparisons.
* **ChatOps Engineering**: Designing interactive, bidirectional webhook callback APIs to integrate third-party communications (Slack Block Kit) with internal script execution state.
