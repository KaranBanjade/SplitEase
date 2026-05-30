output "cloudfront_url" {
  description = "Frontend CloudFront URL (open this in your browser)"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "alb_dns" {
  description = "ALB DNS name – use this to reach the backend API"
  value       = aws_lb.main.dns_name
}

output "ecr_registry" {
  description = "ECR registry base URL for pushing Docker images"
  value       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
}

output "ecr_repositories" {
  description = "Full ECR repository URLs per service"
  value = {
    for svc, repo in aws_ecr_repository.services :
    svc => repo.repository_url
  }
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (host:port)"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint (host)"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "s3_bucket_name" {
  description = "S3 bucket name for the frontend assets"
  value       = aws_s3_bucket.frontend.id
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (needed for cache invalidation in CI/CD)"
  value       = aws_cloudfront_distribution.frontend.id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}
