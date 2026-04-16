resource "aws_iam_role" "iot_box_role" {
  name = "iot_box_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "iot.amazonaws.com"
        }
      }
    ]
  })
}

data "aws_iam_policy" "iot_rule_actions" {
  name = "AWSIoTRuleActions"
}

resource "aws_iam_role_policy_attachment" "iot_rule_actions" {
  role       = aws_iam_role.iot_box_role.name
  policy_arn = data.aws_iam_policy.iot_rule_actions.arn
}

resource "aws_iam_role" "lambda_kinesis_cloudwatch_role" {
  name = "lambda_kinesis_cloudwatch_role"

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

data "aws_iam_policy" "lambda_kinesis_cloudwatch_execution" {
  name = "AWSLambdaKinesisExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_kinesis_cloudwatch_execution" {
  role       = aws_iam_role.lambda_kinesis_cloudwatch_role.name
  policy_arn = data.aws_iam_policy.lambda_kinesis_cloudwatch_execution.arn
}