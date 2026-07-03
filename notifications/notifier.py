import requests
import json
from typing import Optional
from scanner.config import SLACK_WEBHOOK_URL as WEBHOOK_URL
from ai.contracts.recommendation import RecommendationV1
from ai.contracts.policy_result import PolicyValidationResult

def send_alert(
    instance_name,
    instance_id,
    owner,
    cpu_usage,
    monthly_cost,
    account_id="Unknown",
    account_name="Unknown",
    region="Unknown",
    recommendation: Optional[RecommendationV1] = None,
    policy_result: Optional[PolicyValidationResult] = None
):

    button_value = json.dumps({
        "resource_type": "EC2",
        "resource_id": instance_id,
        "account_id": account_id,
        "account_name": account_name,
        "region": region
    })

    main_text = f"""⚠️ *SentinelFinOps Alert*

*Account Name:* {account_name}
*Account ID:* {account_id}
*Region:* {region}

*Instance Name:* {instance_name}
*Instance ID:* {instance_id}

*Owner:* {owner}

*CPU Usage:* {cpu_usage:.2f}%

*Estimated Monthly Cost:* ${monthly_cost:.2f}

*Potential Savings:* ${monthly_cost:.2f}/month

*Recommendation:* Review or Terminate
"""

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": main_text
            }
        }
    ]

    # Present AI recommendation metadata if provided
    if recommendation is not None:
        rec_action = recommendation.recommended_action.value if hasattr(recommendation.recommended_action, "value") else str(recommendation.recommended_action)
        rec_text = (
            f"🤖 *AI Recommendation Details*\n"
            f"*Proposed Action:* {rec_action}\n"
            f"*Confidence Score:* {recommendation.confidence_score:.2f} ({recommendation.confidence_reason})\n"
            f"*Rationale:* {recommendation.reasoning}\n"
        )
        if recommendation.explanation_steps:
            steps_str = "\n".join([f"• {step}" for step in recommendation.explanation_steps])
            rec_text += f"*Explanation:*\n{steps_str}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": rec_text
            }
        })

    # Present Governance policy result if provided
    if policy_result is not None:
        p_status = policy_result.status.value if hasattr(policy_result.status, "value") else str(policy_result.status)
        p_severity = policy_result.severity.value if hasattr(policy_result.severity, "value") else str(policy_result.severity)
        
        status_emoji = "✅" if p_status == "PASSED" else "❌"
        status_label = "PASSED" if p_status == "PASSED" else "BLOCKED/FAILED"
        
        policy_text = (
            f"🛡️ *Policy Validation Result*\n"
            f"*Status:* {status_emoji} {status_label}\n"
            f"*Rule Checked:* `{policy_result.rule_name}`\n"
            f"*Severity:* `{p_severity}`\n"
        )
        if policy_result.violations:
            violations_str = "\n".join([f"• {v}" for v in policy_result.violations])
            policy_text += f"*Violations:*\n{violations_str}"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": policy_text
            }
        })

    # Append actions block
    blocks.append({
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
    })

    payload = {"blocks": blocks}

    response = requests.post(
        WEBHOOK_URL,
        json=payload
    )

    print(
        "Slack Status:",
        response.status_code
    )

def send_ebs_alert(
    volume_id,
    size,
    monthly_savings,
    account_id="Unknown",
    account_name="Unknown",
    region="Unknown",
    recommendation: Optional[RecommendationV1] = None,
    policy_result: Optional[PolicyValidationResult] = None
):
    button_value = json.dumps({
        "resource_type": "EBS",
        "resource_id": volume_id,
        "account_id": account_id,
        "account_name": account_name,
        "region": region
    })

    main_text = f"""⚠️ *Unused EBS Volume Detected*

*Account Name:* {account_name}
*Account ID:* {account_id}
*Region:* {region}

*Volume:*
{volume_id}

*Size:*
{size} GB

*Estimated Savings:*
${monthly_savings:.2f}/month
"""

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": main_text
            }
        }
    ]

    # Present AI recommendation metadata if provided
    if recommendation is not None:
        rec_action = recommendation.recommended_action.value if hasattr(recommendation.recommended_action, "value") else str(recommendation.recommended_action)
        rec_text = (
            f"🤖 *AI Recommendation Details*\n"
            f"*Proposed Action:* {rec_action}\n"
            f"*Confidence Score:* {recommendation.confidence_score:.2f} ({recommendation.confidence_reason})\n"
            f"*Rationale:* {recommendation.reasoning}\n"
        )
        if recommendation.explanation_steps:
            steps_str = "\n".join([f"• {step}" for step in recommendation.explanation_steps])
            rec_text += f"*Explanation:*\n{steps_str}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": rec_text
            }
        })

    # Present Governance policy result if provided
    if policy_result is not None:
        p_status = policy_result.status.value if hasattr(policy_result.status, "value") else str(policy_result.status)
        p_severity = policy_result.severity.value if hasattr(policy_result.severity, "value") else str(policy_result.severity)
        
        status_emoji = "✅" if p_status == "PASSED" else "❌"
        status_label = "PASSED" if p_status == "PASSED" else "BLOCKED/FAILED"
        
        policy_text = (
            f"🛡️ *Policy Validation Result*\n"
            f"*Status:* {status_emoji} {status_label}\n"
            f"*Rule Checked:* `{policy_result.rule_name}`\n"
            f"*Severity:* `{p_severity}`\n"
        )
        if policy_result.violations:
            violations_str = "\n".join([f"• {v}" for v in policy_result.violations])
            policy_text += f"*Violations:*\n{violations_str}"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": policy_text
            }
        })

    # Append actions block
    blocks.append({
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
    })

    payload = {"blocks": blocks}

    response = requests.post(
        WEBHOOK_URL,
        json=payload
    )

    print(
        "Slack Status (EBS):",
        response.status_code
    )
