import os
import requests
import json
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

    button_value = json.dumps({
        "resource_type": "EC2",
        "resource_id": instance_id
    })

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
                    "value": button_value
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "⏰ Snooze"
                    },
                    "action_id": "snooze",
                    "value": button_value
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Auto Fix"
                    },
                    "action_id": "autofix",
                    "value": button_value
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

def send_ebs_alert(volume_id, size, monthly_savings):
    button_value = json.dumps({
        "resource_type": "EBS",
        "resource_id": volume_id
    })

    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"""⚠️ *Unused EBS Volume Detected*

*Volume:*
{volume_id}

*Size:*
{size} GB

*Estimated Savings:*
${monthly_savings:.2f}/month
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
                        "value": button_value
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "⏰ Snooze"
                        },
                        "action_id": "snooze",
                        "value": button_value
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Auto Fix"
                        },
                        "action_id": "autofix",
                        "value": button_value
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
        "Slack Status (EBS):",
        response.status_code
    )