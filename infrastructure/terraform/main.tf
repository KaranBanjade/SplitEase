terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment to store state in S3 (recommended for team usage):
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "splitease/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-state-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ─── Data sources ────────────────────────────────────────────────────────────

data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

# ─── Locals ──────────────────────────────────────────────────────────────────

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  # Use the first two AZs in the region for redundancy
  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  # Services that run on ECS with an exposed HTTP port
  web_services = ["api-gateway", "auth-service", "expense-service"]

  # All services (includes the headless worker)
  all_services = ["api-gateway", "auth-service", "expense-service", "notification-worker"]

  # Port map for web services
  service_ports = {
    api-gateway       = 8000
    auth-service      = 8001
    expense-service   = 8002
  }

  # CPU / memory allocation per service (Fargate vCPU units / MiB)
  service_resources = {
    api-gateway = {
      cpu    = 256
      memory = 512
    }
    auth-service = {
      cpu    = 256
      memory = 512
    }
    expense-service = {
      cpu    = 256
      memory = 512
    }
    notification-worker = {
      cpu    = 128
      memory = 256
    }
  }
}
