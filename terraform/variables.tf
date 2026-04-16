# Uncomment if not using AWS CLI credentials
# variable "aws_access_key" {
#   description = "AWS access key"
#   type        = string
#   sensitive   = true
# }
#
# variable "aws_secret_key" {
#   description = "AWS secret key"
#   type        = string
#   sensitive   = true
# }

variable "influxdb_url" {
  description = "InfluxDB Cloud URL"
  type        = string
}

variable "influxdb_token" {
  description = "InfluxDB API token with read/write access"
  type        = string
  sensitive   = true
}

variable "influxdb_org" {
  description = "InfluxDB organization name"
  type        = string
}

variable "influxdb_bucket" {
  description = "InfluxDB bucket name"
  type        = string
}

variable "grafana_url" {
  description = "Grafana Cloud instance URL"
  type        = string
}

variable "grafana_auth" {
  description = "Grafana service account token"
  type        = string
  sensitive   = true
}
