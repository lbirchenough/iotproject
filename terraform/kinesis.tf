# Kinesis removed 2026-04-17 for cost reasons — IoT Core now invokes Lambda directly
# via an IoT Topic Rule `lambda` action. Kept here for historical reference.

# resource "aws_kinesis_stream" "iot_box_kinesis_stream" {
#   name             = "iot_box_kinesis_stream"
#   shard_count      = 1
#   retention_period = 24
#
# #   shard_level_metrics = [
# #     "IncomingBytes",
# #     "OutgoingBytes",
# #   ]
#
#   stream_mode_details {
#     stream_mode = "PROVISIONED"
#   }
#
# #   tags = {
# #     Environment = "test"
# #   }
# }
