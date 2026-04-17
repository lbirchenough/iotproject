# Package the Lambda function code
data "archive_file" "lambda_function" {
  type = "zip"
  # source_file = "${path.module}/../lambda_function.py"
  source_file = "${path.module}/../lambda_function_no_kinesis.py"
  output_path = "${path.module}/../lambda_function.zip"
}


# Lambda function
resource "aws_lambda_function" "iot_lambda_function" {
  filename      = data.archive_file.lambda_function.output_path
  function_name = "iot_lambda_function"
  # role    = aws_iam_role.lambda_kinesis_cloudwatch_role.arn
  role = aws_iam_role.lambda_cloudwatch_role.arn
  # handler = "lambda_function.lambda_handler"
  handler     = "lambda_function_no_kinesis.lambda_handler"
  code_sha256 = data.archive_file.lambda_function.output_base64sha256

  runtime    = "python3.14"
  depends_on = [aws_cloudwatch_log_group.lambda_logs]

  environment {
    variables = {
      INFLUXDB_URL = var.influxdb_url
      INFLUXDB_TOKEN   = var.influxdb_token
      INFLUXDB_ORG     = var.influxdb_org
      INFLUXDB_BUCKET  = var.influxdb_bucket
    }
  }

#   tags = {
#     Environment = "production"
#     Application = "example"
#   }
}


# Kinesis event source mapping removed 2026-04-17 — IoT Core now invokes Lambda
# directly via an IoT Topic Rule `lambda` action. Kept here for historical reference.
#
# resource "aws_lambda_event_source_mapping" "iot_event_source_mapping" {
#   event_source_arn                   = aws_kinesis_stream.iot_box_kinesis_stream.arn
#   function_name                      = aws_lambda_function.iot_lambda_function.arn
#   starting_position                  = "TRIM_HORIZON"
#   batch_size                         = 10
# #   maximum_batching_window_in_seconds = 5
# #   parallelization_factor             = 2
#
# #   destination_config {
# #     on_failure {
# #       destination_arn = aws_sqs_queue.dlq.arn
# #     }
# #   }
# }

# Allow each IoT Topic Rule to invoke the Lambda function.
resource "aws_lambda_permission" "allow_iot_rule" {
  for_each      = toset(local.box_ids)
  statement_id  = "AllowExecutionFromIoTRule-${each.value}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.iot_lambda_function.function_name
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.iot_core_rule[each.value].arn
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/iot_lambda_function"
  retention_in_days = 1
}
