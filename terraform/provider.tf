terraform {
  required_providers {
    grafana = {
      source = "grafana/grafana"
    }
  }
}

provider "aws" {
  region = "ap-southeast-2"
  # Falls back to AWS CLI credentials (~/.aws/credentials) by default.
  # If not using AWS CLI, uncomment and set in terraform.tfvars:
  # access_key = var.aws_access_key
  # secret_key = var.aws_secret_key
}