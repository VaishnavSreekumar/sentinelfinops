terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# 1. IAM User: sentinelfinops-dev
resource "aws_iam_user" "dev_user" {
  name = "sentinelfinops-dev"
}

# 2. Required IAM permissions (IAM Policy for sentinelfinops-dev)
resource "aws_iam_user_policy" "dev_user_policy" {
  name = "sentinelfinops-dev-policy"
  user = aws_iam_user.dev_user.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "cloudwatch:GetMetricStatistics",
          "cloudtrail:LookupEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# 3. EventBridge schedule (placeholder schedule for future automation)
resource "aws_cloudwatch_event_rule" "schedule_placeholder" {
  name                = "sentinelfinops-automation-schedule"
  description         = "Placeholder schedule for future automation"
  schedule_expression = "rate(1 day)"
  is_enabled          = false
}
