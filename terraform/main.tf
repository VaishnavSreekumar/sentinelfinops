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
          "ec2:CreateImage",
          "ec2:StopInstances",
          "ec2:DescribeImages",
          "ec2:DescribeVolumes",
          "ec2:CreateSnapshot",
          "ec2:DeleteVolume",
          "ec2:DescribeSnapshots",
          "cloudwatch:GetMetricStatistics",
          "cloudtrail:LookupEvents",
          "ce:GetCostAndUsage",
          "pricing:GetProducts"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.snoozes.arn,
          aws_dynamodb_table.audit.arn,
          aws_dynamodb_table.alert_state.arn,
          aws_dynamodb_table.remediation_history.arn,
          aws_dynamodb_table.savings_history.arn,
          aws_dynamodb_table.pricing_cache.arn
        ]
      }
    ]
  })
}

# 3. EventBridge schedule (automated trigger hourly)
resource "aws_cloudwatch_event_rule" "hourly_schedule" {
  name                = "sentinelfinops-hourly-schedule"
  description         = "Trigger SentinelFinOps scan hourly"
  schedule_expression = "rate(1 hour)"
}

# 4. IAM Role for Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "sentinelfinops-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach AWS managed BasicExecutionRole policy for logging
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom policy for scanning permissions (least privilege)
resource "aws_iam_role_policy" "lambda_custom_policy" {
  name = "sentinelfinops-lambda-custom-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:CreateImage",
          "ec2:StopInstances",
          "ec2:DescribeImages",
          "ec2:DescribeVolumes",
          "ec2:CreateSnapshot",
          "ec2:DeleteVolume",
          "ec2:DescribeSnapshots",
          "cloudwatch:GetMetricStatistics",
          "cloudtrail:LookupEvents",
          "ce:GetCostAndUsage",
          "pricing:GetProducts"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.snoozes.arn,
          aws_dynamodb_table.audit.arn,
          aws_dynamodb_table.alert_state.arn,
          aws_dynamodb_table.remediation_history.arn,
          aws_dynamodb_table.savings_history.arn,
          aws_dynamodb_table.pricing_cache.arn
        ]
      }
    ]
  })
}

# Package the application source code and its vendor dependencies
data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "${path.module}/sentinelfinops_lambda.zip"
  source_dir  = "${path.module}/../lambda_package"
}

# 5. Lambda function
resource "aws_lambda_function" "sentinelfinops" {
  filename      = data.archive_file.lambda_zip.output_path
  function_name = "sentinelfinops-scanner"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"

  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  runtime = "python3.11"
  timeout = 300

  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
      AWS_REGION        = var.aws_region
    }
  }




}

# 6. EventBridge Target
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.hourly_schedule.name
  target_id = "sentinelfinops-lambda-target"
  arn       = aws_lambda_function.sentinelfinops.arn
}

# 7. Lambda Permission
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sentinelfinops.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.hourly_schedule.arn
}

resource "aws_dynamodb_table" "snoozes" {
  name         = "sentinelfinops-snoozes"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "instance_id"

  attribute {
    name = "instance_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "audit" {
  name         = "sentinelfinops-audit"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "instance_id"
  range_key    = "timestamp"

  attribute {
    name = "instance_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }
}

resource "aws_dynamodb_table" "alert_state" {
  name         = "sentinelfinops-alert-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "instance_id"

  attribute {
    name = "instance_id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "remediation_history" {
  name         = "sentinelfinops-remediation-history"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "resource_id"
  range_key    = "timestamp"

  attribute {
    name = "resource_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }
}

resource "aws_dynamodb_table" "savings_history" {
  name         = "sentinelfinops-savings-history"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "report_date"
  range_key    = "timestamp"

  attribute {
    name = "report_date"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }
}

resource "aws_dynamodb_table" "pricing_cache" {
  name         = "sentinelfinops-pricing-cache"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cache_key"

  attribute {
    name = "cache_key"
    type = "S"
  }
}
