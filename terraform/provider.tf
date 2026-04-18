terraform {
  required_providers {
    grafana = {
      source = "grafana/grafana"
    }
  }

  # Partial backend config — bucket and region are supplied at init time via
  # terraform/backend.hcl (gitignored). See backend.hcl.example and the README
  # section "Terraform State — Local vs. S3 Backend" for setup instructions.
  # For local state instead, comment out this whole block.
  backend "s3" {
    key          = "iotproject/terraform.tfstate"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = "ap-southeast-2"
  # Falls back to AWS CLI credentials (~/.aws/credentials) by default.
  # If not using AWS CLI, uncomment and set in terraform.tfvars:
  # access_key = var.aws_access_key
  # secret_key = var.aws_secret_key
}