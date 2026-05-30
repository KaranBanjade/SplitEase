# ─── ECS Cluster ─────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"   # Disable to save ~$0.30/GB CloudWatch metrics cost
  }

  tags = {
    Name = "${local.name_prefix}-cluster"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }
}

# ─── IAM – Task Execution Role (ECS control-plane operations) ─────────────────

resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.name_prefix}-ecs-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Name = "${local.name_prefix}-ecs-task-execution"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_managed" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow the execution role to read SSM parameters (for secrets injection)
resource "aws_iam_role_policy" "ecs_task_execution_ssm" {
  name = "${local.name_prefix}-ecs-execution-ssm"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameters",
          "ssm:GetParameter",
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/*",
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/*"
        ]
      }
    ]
  })
}

# ─── IAM – Task Role (application-level AWS access) ──────────────────────────

resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Name = "${local.name_prefix}-ecs-task"
  }
}

# Minimal permissions: read SSM parameters at runtime + write CloudWatch logs
resource "aws_iam_role_policy" "ecs_task_permissions" {
  name = "${local.name_prefix}-ecs-task-permissions"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# ─── SSM Parameters (secrets) ─────────────────────────────────────────────────

resource "aws_ssm_parameter" "db_url" {
  name  = "/${var.project_name}/DATABASE_URL"
  type  = "SecureString"
  value = "postgresql+asyncpg://splitease:${var.db_password}@${aws_db_instance.postgres.endpoint}/splitease"

  tags = {
    Name = "${local.name_prefix}-db-url"
  }
}

resource "aws_ssm_parameter" "redis_url" {
  name  = "/${var.project_name}/REDIS_URL"
  type  = "SecureString"
  value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379"

  tags = {
    Name = "${local.name_prefix}-redis-url"
  }
}

resource "aws_ssm_parameter" "secret_key" {
  name  = "/${var.project_name}/SECRET_KEY"
  type  = "SecureString"
  value = var.secret_key

  tags = {
    Name = "${local.name_prefix}-secret-key"
  }
}

resource "aws_ssm_parameter" "smtp_password" {
  count = var.smtp_password != "" ? 1 : 0

  name  = "/${var.project_name}/SMTP_PASSWORD"
  type  = "SecureString"
  value = var.smtp_password

  tags = {
    Name = "${local.name_prefix}-smtp-password"
  }
}

resource "aws_ssm_parameter" "vapid_private_key" {
  count = var.vapid_private_key != "" ? 1 : 0

  name  = "/${var.project_name}/VAPID_PRIVATE_KEY"
  type  = "SecureString"
  value = var.vapid_private_key

  tags = {
    Name = "${local.name_prefix}-vapid-private-key"
  }
}

# ─── CloudWatch Log Groups ────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "services" {
  for_each = toset(local.all_services)

  name              = "/ecs/${local.name_prefix}/${each.key}"
  retention_in_days = 30

  tags = {
    Name = "${local.name_prefix}-${each.key}-logs"
  }
}

# ─── Application Load Balancer ────────────────────────────────────────────────

resource "aws_lb" "main" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = var.environment == "production" ? true : false

  tags = {
    Name = "${local.name_prefix}-alb"
  }
}

# Target group for the api-gateway (single entry-point for all backend traffic)
resource "aws_lb_target_group" "api_gateway" {
  name        = "${local.name_prefix}-api-gw-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = {
    Name = "${local.name_prefix}-api-gw-tg"
  }
}

# HTTP listener – redirect to HTTPS (no-op when no domain/cert is configured)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# Fallback HTTP listener rule – forward directly when HTTPS is not available
# (Remove this and the redirect above once you attach an ACM certificate.)
resource "aws_lb_listener" "http_forward" {
  load_balancer_arn = aws_lb.main.arn
  port              = 8080
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_gateway.arn
  }

  # Remove this listener once HTTPS is configured
  tags = {
    Note = "Remove after adding ACM certificate"
  }
}

# ─── ECS Task Definitions ─────────────────────────────────────────────────────

# api-gateway
resource "aws_ecs_task_definition" "api_gateway" {
  family                   = "${local.name_prefix}-api-gateway"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = local.service_resources["api-gateway"].cpu
  memory                   = local.service_resources["api-gateway"].memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "api-gateway"
    image     = "${aws_ecr_repository.services["api-gateway"].repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "AUTH_SERVICE_URL",    value = "http://localhost:8001" },
      { name = "EXPENSE_SERVICE_URL", value = "http://localhost:8002" },
      { name = "ENVIRONMENT",         value = var.environment },
    ]

    secrets = [
      { name = "REDIS_URL",   valueFrom = aws_ssm_parameter.redis_url.arn },
      { name = "SECRET_KEY",  valueFrom = aws_ssm_parameter.secret_key.arn },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.services["api-gateway"].name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = {
    Name = "${local.name_prefix}-api-gateway-td"
  }
}

# auth-service
resource "aws_ecs_task_definition" "auth_service" {
  family                   = "${local.name_prefix}-auth-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = local.service_resources["auth-service"].cpu
  memory                   = local.service_resources["auth-service"].memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "auth-service"
    image     = "${aws_ecr_repository.services["auth-service"].repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8001
      protocol      = "tcp"
    }]

    environment = [
      { name = "ENVIRONMENT",  value = var.environment },
      { name = "SMTP_HOST",    value = var.smtp_host },
      { name = "SMTP_PORT",    value = "587" },
      { name = "SMTP_USER",    value = var.smtp_user },
      { name = "FROM_EMAIL",   value = "noreply@splitease.app" },
      { name = "APP_URL",      value = "https://${aws_cloudfront_distribution.frontend.domain_name}" },
    ]

    secrets = [
      { name = "DATABASE_URL",  valueFrom = aws_ssm_parameter.db_url.arn },
      { name = "REDIS_URL",     valueFrom = aws_ssm_parameter.redis_url.arn },
      { name = "SECRET_KEY",    valueFrom = aws_ssm_parameter.secret_key.arn },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.services["auth-service"].name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = {
    Name = "${local.name_prefix}-auth-service-td"
  }
}

# expense-service
resource "aws_ecs_task_definition" "expense_service" {
  family                   = "${local.name_prefix}-expense-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = local.service_resources["expense-service"].cpu
  memory                   = local.service_resources["expense-service"].memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "expense-service"
    image     = "${aws_ecr_repository.services["expense-service"].repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8002
      protocol      = "tcp"
    }]

    environment = [
      { name = "AUTH_SERVICE_URL", value = "http://${aws_lb.main.dns_name}:8080/auth" },
      { name = "ENVIRONMENT",      value = var.environment },
    ]

    secrets = [
      { name = "DATABASE_URL", valueFrom = aws_ssm_parameter.db_url.arn },
      { name = "SECRET_KEY",   valueFrom = aws_ssm_parameter.secret_key.arn },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.services["expense-service"].name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8002/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = {
    Name = "${local.name_prefix}-expense-service-td"
  }
}

# notification-worker (no port – background process)
resource "aws_ecs_task_definition" "notification_worker" {
  family                   = "${local.name_prefix}-notification-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = local.service_resources["notification-worker"].cpu
  memory                   = local.service_resources["notification-worker"].memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "notification-worker"
    image     = "${aws_ecr_repository.services["notification-worker"].repository_url}:latest"
    essential = true

    environment = [
      { name = "AUTH_SERVICE_URL",    value = "http://${aws_lb.main.dns_name}:8080/auth" },
      { name = "EXPENSE_SERVICE_URL", value = "http://${aws_lb.main.dns_name}:8080/expenses" },
      { name = "SMTP_HOST",           value = var.smtp_host },
      { name = "SMTP_PORT",           value = "587" },
      { name = "SMTP_USER",           value = var.smtp_user },
      { name = "FROM_EMAIL",          value = "noreply@splitease.app" },
      { name = "APP_URL",             value = "https://${aws_cloudfront_distribution.frontend.domain_name}" },
      { name = "VAPID_PUBLIC_KEY",    value = var.vapid_public_key },
      { name = "ENVIRONMENT",         value = var.environment },
    ]

    secrets = [
      { name = "DATABASE_URL",    valueFrom = aws_ssm_parameter.db_url.arn },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.services["notification-worker"].name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])

  tags = {
    Name = "${local.name_prefix}-notification-worker-td"
  }
}

# ─── ECS Services ─────────────────────────────────────────────────────────────

resource "aws_ecs_service" "api_gateway" {
  name            = "${local.name_prefix}-api-gateway"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api_gateway.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api_gateway.arn
    container_name   = "api-gateway"
    container_port   = 8000
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  depends_on = [aws_lb_listener.http_forward]

  lifecycle {
    ignore_changes = [task_definition]   # Managed by CI/CD pipeline
  }

  tags = {
    Name = "${local.name_prefix}-api-gateway-svc"
  }
}

resource "aws_ecs_service" "auth_service" {
  name            = "${local.name_prefix}-auth-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.auth_service.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = {
    Name = "${local.name_prefix}-auth-service-svc"
  }
}

resource "aws_ecs_service" "expense_service" {
  name            = "${local.name_prefix}-expense-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.expense_service.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = {
    Name = "${local.name_prefix}-expense-service-svc"
  }
}

resource "aws_ecs_service" "notification_worker" {
  name            = "${local.name_prefix}-notification-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.notification_worker.arn
  desired_count   = 1   # Always exactly 1 worker
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = {
    Name = "${local.name_prefix}-notification-worker-svc"
  }
}
