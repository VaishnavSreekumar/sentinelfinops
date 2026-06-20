output "lambda_function_arn" {
  value       = aws_lambda_function.sentinelfinops.arn
  description = "The ARN of the SentinelFinOps scanner Lambda function."
}

output "eventbridge_rule_arn" {
  value       = aws_cloudwatch_event_rule.hourly_schedule.arn
  description = "The ARN of the EventBridge scheduling rule."
}
