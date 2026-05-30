# SplitEase – Deployment Guide

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [First-time AWS Setup (Terraform)](#2-first-time-aws-setup-terraform)
3. [GitHub Actions Setup (CI/CD)](#3-github-actions-setup-cicd)
4. [Local Development](#4-local-development)
5. [Running Migrations](#5-running-migrations)
6. [Environment Variables Reference](#6-environment-variables-reference)
7. [Monitoring & Logs](#7-monitoring--logs)
8. [Cost Breakdown](#8-cost-breakdown)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites

Install the following tools before you begin:

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | 24+ | https://docs.docker.com/get-docker/ |
| Docker Compose | 2.20+ | Bundled with Docker Desktop |
| Node.js | 20 LTS | https://nodejs.org |
| Python | 3.12+ | https://python.org |
| AWS CLI | 2.x | `brew install awscli` or https://aws.amazon.com/cli/ |
| Terraform | 1.5+ | `brew install terraform` or https://terraform.io |
| Make | any | Pre-installed on macOS/Linux; Windows: `choco install make` |

Verify everything is installed:

```bash
docker --version && docker compose version
node --version && npm --version
python3 --version
aws --version
terraform --version
```

---

## 2. First-time AWS Setup (Terraform)

### 2.1 Configure AWS CLI

```bash
aws configure
# Enter your AWS Access Key ID, Secret, region (us-east-1), and output format (json)
```

> If you use AWS SSO, run `aws sso login --profile your-profile` instead.

### 2.2 Create the Terraform variables file

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with real values:

```hcl
project_name = "splitease"
environment  = "production"
aws_region   = "us-east-1"

# Generate with: openssl rand -base64 24
db_password  = "MyStr0ng-DB-P@ssword"

# Generate with: make generate-secret (or: openssl rand -hex 32)
secret_key   = "a3f1c8e2d9b4..."

# Optional email/push
smtp_host         = "smtp.gmail.com"
smtp_user         = "you@gmail.com"
smtp_password     = "app-specific-password"
vapid_private_key = "..."   # from: make generate-vapid
vapid_public_key  = "..."
```

> **Never commit `terraform.tfvars`** – it is git-ignored. Use AWS Secrets Manager
> or CI/CD secrets for production credentials.

### 2.3 Initialise and apply Terraform

```bash
cd infrastructure/terraform

# Download provider plugins
terraform init

# Preview the changes (read-only)
terraform plan

# Apply – this creates all AWS resources (takes ~10 minutes)
terraform apply
```

Terraform will output the key values you need for the next steps:

```
cloudfront_url             = "https://d1abc123.cloudfront.net"
alb_dns                    = "splitease-production-alb-123456.us-east-1.elb.amazonaws.com"
ecr_registry               = "123456789012.dkr.ecr.us-east-1.amazonaws.com"
s3_bucket_name             = "splitease-production-frontend-123456789012"
cloudfront_distribution_id = "ABCDEFGHIJ"
```

Save these – you'll set them as GitHub repository variables in the next step.

### 2.4 Push initial Docker images

Before ECS can start any tasks, each ECR repository needs at least one image:

```bash
# Log in to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Build and push each service
for svc in api-gateway auth-service expense-service notification-worker; do
  docker build -t splitease-${svc} ./services/${svc}
  docker tag splitease-${svc}:latest \
    123456789012.dkr.ecr.us-east-1.amazonaws.com/splitease-${svc}:latest
  docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/splitease-${svc}:latest
done
```

### 2.5 Run database migrations on RDS

The ECS tasks can access RDS only from within the VPC. The simplest approach
for an initial migration is to temporarily run a migration task:

```bash
# Option A: Run via a one-off ECS task (recommended for production)
aws ecs run-task \
  --cluster splitease-production-cluster \
  --task-definition splitease-production-auth-service \
  --overrides '{"containerOverrides":[{"name":"auth-service","command":["alembic","upgrade","head"]}]}' \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"

# Option B: Use a bastion host or AWS Systems Manager Session Manager tunnel
# (see Troubleshooting section)
```

---

## 3. GitHub Actions Setup (CI/CD)

### 3.1 Create the OIDC IAM role for GitHub Actions

This allows GitHub Actions to authenticate with AWS **without storing long-lived
access keys**. The Terraform state already created the necessary IAM trust policy
scaffolding; you just need to create the role manually once:

```bash
# Create the OIDC provider for GitHub (once per AWS account)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# Create the deploy role
aws iam create-role \
  --role-name splitease-github-deploy \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
        }
      }
    }]
  }'

# Attach necessary permissions
aws iam attach-role-policy \
  --role-name splitease-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess

aws iam attach-role-policy \
  --role-name splitease-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam attach-role-policy \
  --role-name splitease-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy \
  --role-name splitease-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/CloudFrontFullAccess
```

### 3.2 Configure repository secrets and variables

Go to your GitHub repository → **Settings → Secrets and variables → Actions**.

**Repository Secrets** (encrypted):

| Secret | Value |
|--------|-------|
| `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::123456789012:role/splitease-github-deploy` |

**Repository Variables** (plain text – not secret):

| Variable | Value | Example |
|----------|-------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `ECR_REGISTRY` | ECR registry URL | `123456789012.dkr.ecr.us-east-1.amazonaws.com` |
| `S3_BUCKET` | Frontend S3 bucket name | `splitease-production-frontend-123456789012` |
| `CLOUDFRONT_DISTRIBUTION_ID` | CF distribution ID | `ABCDEFGHIJ` |
| `API_URL` | Backend API URL | `https://api.yourdomain.com` or `/api` |
| `VAPID_PUBLIC_KEY` | VAPID public key | (from `make generate-vapid`) |
| `ALB_DNS` | ALB DNS name | `splitease-...elb.amazonaws.com` |

### 3.3 Trigger your first deployment

```bash
git push origin main
```

The CI pipeline (`.github/workflows/ci.yml`) runs on every push. The deploy
pipeline (`.github/workflows/deploy.yml`) triggers on pushes to `main`.

Monitor the deployment in the **Actions** tab on GitHub.

---

## 4. Local Development

### 4.1 First-time setup (one command)

```bash
make dev-setup
```

This command:

1. Copies `.env.example` → `.env` (if `.env` doesn't exist yet).
2. Builds all Docker images.
3. Starts all services.
4. Waits 15 seconds for services to become healthy.
5. Runs database migrations.
6. Seeds the database with test data.

When complete, open:

- Frontend: http://localhost:3000
- API Gateway + Swagger UI: http://localhost:8000/docs
- Auth Service Swagger: http://localhost:8001/docs
- Expense Service Swagger: http://localhost:8002/docs

### 4.2 Day-to-day development

```bash
make up          # Start services (after first setup)
make down        # Stop services
make logs        # Tail all logs
make logs-auth   # Tail only auth-service logs

# Hot-reload is enabled – edit Python files and uvicorn restarts automatically.
# Edit frontend files in apps/web/src – Vite HMR applies changes instantly.
```

### 4.3 Connecting to services

```bash
make shell-auth   # bash inside auth-service container
make shell-db     # psql connected to splitease DB
make shell-redis  # redis-cli
```

---

## 5. Running Migrations

Migrations are managed with **Alembic** inside each Python service.

### Running migrations locally

```bash
make migrate          # Run auth + expense migrations
make migrate-auth     # Auth service only
make migrate-expense  # Expense service only
```

### Creating a new migration

```bash
# Enter the service container
make shell-auth

# Inside the container:
alembic revision --autogenerate -m "add avatar_url to users"
# Alembic inspects the SQLAlchemy models and generates a migration file.

# Review the generated file in services/auth-service/alembic/versions/
# Then apply it:
alembic upgrade head
```

### Rolling back

```bash
# Inside the service container:
alembic downgrade -1    # Revert one migration
alembic downgrade base  # Revert all migrations (DESTRUCTIVE)
```

---

## 6. Environment Variables Reference

All variables are defined in `.env.example`. The table below documents each one:

### Database & Cache

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | asyncpg connection string |
| `REDIS_URL` | Yes | Redis connection URL |

### Authentication

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | 256-bit hex secret for JWT signing. Generate: `openssl rand -hex 32` |

### Service Discovery

| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH_SERVICE_URL` | Gateway only | Internal URL of auth-service |
| `EXPENSE_SERVICE_URL` | Gateway only | Internal URL of expense-service |

### Email

| Variable | Required | Description |
|----------|----------|-------------|
| `SMTP_HOST` | No | SMTP server (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | No | SMTP port (default: `587` for STARTTLS) |
| `SMTP_USER` | No | SMTP username / sender email |
| `SMTP_PASSWORD` | No | SMTP password or app-specific password |
| `FROM_EMAIL` | No | From address for outgoing emails |

> Gmail: enable 2FA, then create an [App Password](https://support.google.com/accounts/answer/185833).
> For production, use **AWS SES** – cheaper and more reliable.

### Web Push (VAPID)

| Variable | Required | Description |
|----------|----------|-------------|
| `VAPID_PRIVATE_KEY` | No | VAPID private key (worker only) |
| `VAPID_PUBLIC_KEY` | No | VAPID public key (worker + frontend) |
| `VAPID_CLAIMS_EMAIL` | No | Contact email in VAPID claims |

Generate keys: `make generate-vapid`

### Application

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_URL` | Yes | Base URL of the frontend (used in email links) |
| `ENVIRONMENT` | Yes | `development`, `test`, or `production` |

---

## 7. Monitoring & Logs

### CloudWatch Logs

Each ECS service streams logs to its own CloudWatch log group:

```
/ecs/splitease-production/api-gateway
/ecs/splitease-production/auth-service
/ecs/splitease-production/expense-service
/ecs/splitease-production/notification-worker
```

View logs in the console:

```
AWS Console → CloudWatch → Log groups → /ecs/splitease-production/api-gateway
```

Or via CLI:

```bash
aws logs tail /ecs/splitease-production/api-gateway --follow
```

### Useful CloudWatch Insights queries

**Error rate in the last hour:**

```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 50
```

**Slow requests (>1s) on the gateway:**

```
fields @timestamp, @message
| filter @message like /duration_ms/
| parse @message "duration_ms=*" as duration
| filter duration > 1000
| sort duration desc
```

### Recommended CloudWatch Alarms

Create these alarms after deploying (adapt thresholds to your traffic):

```bash
# ECS service unhealthy task count
aws cloudwatch put-metric-alarm \
  --alarm-name "splitease-api-gateway-unhealthy" \
  --metric-name "UnhealthyHostCount" \
  --namespace "AWS/ApplicationELB" \
  --dimensions Name=TargetGroup,Value=... \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:...:alerts

# RDS free storage below 5 GiB
aws cloudwatch put-metric-alarm \
  --alarm-name "splitease-rds-low-storage" \
  --metric-name "FreeStorageSpace" \
  --namespace "AWS/RDS" \
  --dimensions Name=DBInstanceIdentifier,Value=splitease-production-postgres \
  --statistic Average \
  --period 300 \
  --threshold 5368709120 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1
```

---

## 8. Cost Breakdown

Estimated monthly costs for a lightly-loaded production deployment in us-east-1:

| Resource | Spec | Monthly cost |
|----------|------|-------------|
| ECS Fargate | 4 tasks × 256 CPU / 512 MB | ~$8 |
| RDS PostgreSQL | db.t4g.micro, 20 GiB gp3, single-AZ | ~$12 |
| ElastiCache Redis | cache.t3.micro, single node | ~$12 |
| Application Load Balancer | 1 ALB, ~1 GB processed/month | ~$16 |
| NAT Gateway | 1 gateway, ~5 GB data | ~$32 |
| CloudFront | PriceClass_100, ~10 GB transfer | ~$1 |
| S3 | 500 MB storage, ~1 GB transfer | <$1 |
| ECR | 4 repos, ~2 GB storage | ~$1 |
| CloudWatch Logs | 30-day retention, ~5 GB/month | ~$2 |
| **Total** | | **~$85/month** |

### Cost reduction options

1. **Remove NAT Gateway** (saves ~$32/month): Assign public IPs to ECS tasks
   and restrict outbound traffic via security groups. Loses the security benefit
   of private subnets.

2. **Stop the ECS services when not in use**: Set `desired_count = 0` on
   non-business hours. Saves proportional Fargate cost.

3. **Use Reserved Instances for RDS**: 1-year reserved db.t4g.micro saves ~40%
   (~$5/month).

4. **Reduce log retention**: Change from 30 days to 7 days in `ecs.tf`.

5. **Use FARGATE_SPOT**: Change capacity provider strategy to prefer
   `FARGATE_SPOT` for stateless services – saves up to 70% on Fargate costs.
   Note: spot tasks can be interrupted; ensure graceful shutdown.

---

## 9. Troubleshooting

### "Service not healthy" after `make up`

```bash
# Check which container is failing
docker compose ps

# Inspect logs of the failing service
make logs-auth   # or logs-expense, logs-gateway

# Common causes:
# 1. Missing SECRET_KEY in .env – generate with: make generate-secret
# 2. Migrations not run – run: make migrate
# 3. Port already in use – stop conflicting services
```

### "Cannot connect to database"

```bash
# Verify postgres is healthy
docker compose ps postgres

# Connect directly
make shell-db

# Check the DATABASE_URL in .env matches what's in docker-compose.yml
```

### Alembic "target database is not up to date"

```bash
# Check current revision
docker compose exec auth-service alembic current

# Check what's pending
docker compose exec auth-service alembic history

# Apply pending migrations
make migrate
```

### ECS tasks keep crashing in production

```bash
# List recent stopped tasks and their stop reasons
aws ecs list-tasks --cluster splitease-production --desired-status STOPPED
aws ecs describe-tasks --cluster splitease-production --tasks TASK_ARN \
  --query 'tasks[].stoppedReason'

# Check logs
aws logs tail /ecs/splitease-production/api-gateway --since 30m
```

### CloudFront returns 403 for all requests

This usually means the S3 bucket policy is not correctly allowing CloudFront OAC.
Re-apply Terraform:

```bash
cd infrastructure/terraform
terraform apply -target=aws_s3_bucket_policy.frontend
```

### Push notifications not working

1. Check VAPID keys are set in `.env` (or SSM in production).
2. Ensure the browser has granted notification permission.
3. Check notification-worker logs: `make logs-worker`.
4. Verify the worker is connected to the database.
