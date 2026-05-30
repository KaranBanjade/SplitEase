# ─── ElastiCache Subnet Group ─────────────────────────────────────────────────

resource "aws_elasticache_subnet_group" "redis" {
  name        = "${local.name_prefix}-redis-subnet-group"
  description = "Subnet group for SplitEase ElastiCache Redis"
  subnet_ids  = aws_subnet.private[*].id

  tags = {
    Name = "${local.name_prefix}-redis-subnet-group"
  }
}

# ─── ElastiCache Parameter Group ──────────────────────────────────────────────

resource "aws_elasticache_parameter_group" "redis" {
  name        = "${local.name_prefix}-redis7"
  family      = "redis7"
  description = "SplitEase Redis 7 parameter group"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"   # Evict least-recently-used keys when memory is full
  }

  tags = {
    Name = "${local.name_prefix}-redis7"
  }
}

# ─── ElastiCache Cluster ──────────────────────────────────────────────────────

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${local.name_prefix}-redis"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1      # Single node – no cluster mode needed at this scale
  parameter_group_name = aws_elasticache_parameter_group.redis.name
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]

  # Maintenance window
  maintenance_window = "sun:05:00-sun:06:00"

  # Snapshot / backup
  snapshot_retention_limit = 1
  snapshot_window          = "03:00-04:00"

  # Apply changes immediately during the maintenance window
  apply_immediately = false

  tags = {
    Name = "${local.name_prefix}-redis"
  }
}
