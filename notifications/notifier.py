import os
import requests
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.getenv(
    "SLACK_WEBHOOK_URL"
)

def send_alert(
    instance_name,
    instance_id,
    owner,
    cpu_usage,
    monthly_cost
):

    payload = {
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"""⚠️ *SentinelFinOps Alert*

*Instance Name:* {instance_name}
*Instance ID:* {instance_id}

*Owner:* {owner}

*CPU Usage:* {cpu_usage:.2f}%

*Estimated Monthly Cost:* ${monthly_cost:.2f}

*Potential Savings:* ${monthly_cost:.2f}/month

*Recommendation:* Review or Terminate
"""
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Acknowledge"
                    },
                    "action_id": "acknowledge",
                    "value": instance_id
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "⏰ Snooze"
                    },
                    "action_id": "snooze",
                    "value": instance_id
                }
            ]
        }
    ]
}

    response = requests.post(
        WEBHOOK_URL,
        json=payload
    )

    print(
        "Slack Status:",
        response.status_code
    )