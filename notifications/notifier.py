import os
import requests
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.getenv(
    "SLACK_WEBHOOK_URL"
)

def send_alert(
    instance_id,
    cpu_usage,
    monthly_cost
):

    payload = {
        "text": f"""
⚠️ SentinelFinOps Alert

Instance ID: {instance_id}

CPU Usage: {cpu_usage:.2f}%

Estimated Monthly Cost: ${monthly_cost:.2f}

Potential Savings: ${monthly_cost:.2f}/month

Recommendation: Review or Terminate
"""
    }

    response = requests.post(
        WEBHOOK_URL,
        json=payload
    )

    print(
        "Slack Status:",
        response.status_code
    )