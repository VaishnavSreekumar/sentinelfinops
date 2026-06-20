variable "aws_region" {
  type        = string
  description = "AWS region for resources"
  default     = "ap-south-1"
}

variable "slack_webhook_url" {
  type        = string
  description = "Slack webhook URL for alerts"
  default     = ""
}
