locals {
  box_ids = ["box1", "box2"]
}

data "aws_iot_endpoint" "iot_box_endpoint" {
  endpoint_type = "iot:Data-ATS"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "local_file" "terraform_config" {
  filename = "${path.module}/../terraform_config.py"
  content  = "AWS_ENDPOINT = \"${data.aws_iot_endpoint.iot_box_endpoint.endpoint_address}\"\n"
}

resource "aws_iot_thing" "iot_box" {
  for_each = toset(local.box_ids)
  name     = "iot_${each.value}"
}

resource "aws_iot_certificate" "iot_box_cert" {
  for_each = toset(local.box_ids)
  active   = true
}

resource "local_file" "iot_box_cert" {
  for_each = toset(local.box_ids)
  content  = aws_iot_certificate.iot_box_cert[each.value].certificate_pem
  filename = "${path.module}/../certs/iot_${each.value}.pem"
}

resource "local_file" "iot_box_key" {
  for_each = toset(local.box_ids)
  content  = aws_iot_certificate.iot_box_cert[each.value].private_key
  filename = "${path.module}/../certs/iot_${each.value}.key"
}

resource "aws_iot_policy" "iot_box_policy" {
  for_each = toset(local.box_ids)
  name     = "iot_${each.value}_policy"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : "iot:Connect",
        "Resource" : "arn:aws:iot:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:client/${aws_iot_thing.iot_box[each.value].name}"
      },
      {
        "Effect" : "Allow",
        "Action" : "iot:Publish",
        "Resource" : "arn:aws:iot:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:topic/${aws_iot_thing.iot_box[each.value].name}/*"
      }
    ]
  })
}

resource "aws_iot_policy_attachment" "iot_box_policy_attachment" {
  for_each = toset(local.box_ids)
  policy   = aws_iot_policy.iot_box_policy[each.value].name
  target   = aws_iot_certificate.iot_box_cert[each.value].arn
}

resource "aws_iot_topic_rule" "iot_core_rule" {
  for_each = toset(local.box_ids)

  # name        = "iot_${each.value}_kinesis"
  # description = "Sending iot_${each.value} data to Kinesis stream"
  name        = "iot_${each.value}_lambda"
  description = "Forwarding iot_${each.value} data directly to Lambda"

  enabled     = true
  sql         = "SELECT * FROM 'iot_${each.value}/#'"
  sql_version = "2016-03-23"

  # kinesis {
  #   stream_name   = aws_kinesis_stream.iot_box_kinesis_stream.name
  #   role_arn      = aws_iam_role.iot_box_role.arn
  #   partition_key = "$${topic()}"
  # }

  lambda {
    function_arn = aws_lambda_function.iot_lambda_function.arn
  }
}
