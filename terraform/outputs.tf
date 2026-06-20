output "iam_user_arn" {
  value       = aws_iam_user.dev_user.arn
  description = "The ARN of the sentinelfinops-dev IAM user."
}

output "eventbridge_rule_arn" {
  value       = aws_cloudwatch_event_rule.schedule_placeholder.arn
  description = "The ARN of the EventBridge placeholder rule."
}
