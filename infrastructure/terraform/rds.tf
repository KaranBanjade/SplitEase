# ─── DB Subnet Group ──────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "postgres" {
  name        = "${local.name_prefix}-db-subnet-group"
  description = "Subnet group for SplitEase RDS instance"
  subnet_ids  = aws_subnet.private[*].id

  tags = {
    Name = "${local.name_prefix}-db-subnet-group"
  }
}

# ─── Parameter Group ──────────────────────────────────────────────────────────

resource "aws_db_parameter_group" "postgres" {
  name        = "${local.name_prefix}-pg16"
  family      = "postgres16"
  description = "SplitEase PostgreSQL 16 parameter group"

  parameter {
    name  = "timezone"
    value = "UTC"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  tags = {
    Name = "${local.name_prefix}-pg16"
  }
}

# ─── RDS Instance ─────────────────────────────────────────────────────────────

resource "aws_db_instance" "postgres" {
  identifier = "${local.name_prefix}-postgres"

  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro"   # Graviton2 – better value than t3.micro

  db_name  = "splitease"
  username = "splitease"
  password = var.db_password

  # Storage
  allocated_storage     = 20
  max_allocated_storage = 100   # Enable autoscaling up to 100 GiB
  storage_type          = "gp3"
  storage_encrypted     = true

  # Network / security
  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Parameter & option groups
  parameter_group_name = aws_db_parameter_group.postgres.name

  # Backup / maintenance
  backup_retention_period = 7
  backup_window           = "02:00-03:00"
  maintenance_window      = "sun:04:00-sun:05:00"
  copy_tags_to_snapshot   = true

  # High availability
  multi_az = false   # Single-AZ for cost savings; set true for production HA

  # Deletion protection – prevents accidental destroy in production
  deletion_protection = var.environment == "production" ? true : false
  skip_final_snapshot = var.environment == "production" ? false : true
  final_snapshot_identifier = var.environment == "production" ? "${local.name_prefix}-final-snapshot" : null

  # Performance Insights (free tier available)
  performance_insights_enabled = true

  tags = {
    Name = "${local.name_prefix}-postgres"
  }
}
