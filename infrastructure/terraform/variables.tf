variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "splitease"
}

variable "environment" {
  description = "Environment (production, staging)"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "db_password" {
  description = "PostgreSQL master password"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "JWT secret key (256-bit hex, generate with: openssl rand -hex 32)"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Custom domain name for CloudFront (leave empty to use the generated *.cloudfront.net domain)"
  type        = string
  default     = ""
}

variable "smtp_host" {
  description = "SMTP server hostname"
  type        = string
  default     = ""
}

variable "smtp_user" {
  description = "SMTP username / email address"
  type        = string
  default     = ""
}

variable "smtp_password" {
  description = "SMTP password or app-specific password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "vapid_private_key" {
  description = "VAPID private key for Web Push notifications"
  type        = string
  sensitive   = true
  default     = ""
}

variable "vapid_public_key" {
  description = "VAPID public key for Web Push notifications"
  type        = string
  default     = ""
}

variable "ecs_desired_count" {
  description = "Desired number of ECS task replicas per service"
  type        = number
  default     = 1
}
