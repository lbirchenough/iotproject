# IoT rule action role removed 2026-04-17 — the `lambda` action on a topic rule uses
# a resource-based policy (aws_lambda_permission) instead of an IAM role, so this
# role is no longer referenced. Kept here for historical reference.
#
# resource "aws_iam_role" "iot_box_role" {
#   name = "iot_box_role"
#
#   assume_role_policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Action = "sts:AssumeRole"
#         Effect = "Allow"
#         Principal = {
#           Service = "iot.amazonaws.com"
#         }
#       }
#     ]
#   })
# }
#
# data "aws_iam_policy" "iot_rule_actions" {
#   name = "AWSIoTRuleActions"
# }
#
# resource "aws_iam_role_policy_attachment" "iot_rule_actions" {
#   role       = aws_iam_role.iot_box_role.name
#   policy_arn = data.aws_iam_policy.iot_rule_actions.arn
# }

# Lambda execution role with Kinesis read + CloudWatch logs. Kept for historical
# reference — replaced by `lambda_cloudwatch_role` below which only needs CloudWatch
# logs now that Lambda is invoked directly by IoT Core rather than reading Kinesis.
#
# resource "aws_iam_role" "lambda_kinesis_cloudwatch_role" {
#   name = "lambda_kinesis_cloudwatch_role"
#
#   assume_role_policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Action = "sts:AssumeRole"
#         Effect = "Allow"
#         Principal = {
#           Service = "lambda.amazonaws.com"
#         }
#       }
#     ]
#   })
# }
#
# data "aws_iam_policy" "lambda_kinesis_cloudwatch_execution" {
#   name = "AWSLambdaKinesisExecutionRole"
# }
#
# resource "aws_iam_role_policy_attachment" "lambda_kinesis_cloudwatch_execution" {
#   role       = aws_iam_role.lambda_kinesis_cloudwatch_role.name
#   policy_arn = data.aws_iam_policy.lambda_kinesis_cloudwatch_execution.arn
# }

resource "aws_iam_role" "lambda_cloudwatch_role" {
  name = "lambda_cloudwatch_role"

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

data "aws_iam_policy" "lambda_basic_execution" {
  name = "AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_cloudwatch_role.name
  policy_arn = data.aws_iam_policy.lambda_basic_execution.arn
}
