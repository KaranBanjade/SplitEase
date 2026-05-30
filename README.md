<!-- Badges -->
[![CI](https://github.com/your-org/splitease/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/splitease/actions/workflows/ci.yml)
[![Deploy](https://github.com/your-org/splitease/actions/workflows/deploy.yml/badge.svg)](https://github.com/your-org/splitease/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Built with React](https://img.shields.io/badge/Frontend-React-61DAFB?logo=react)](https://react.dev)
[![Infrastructure: Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform)](https://terraform.io)

# SplitEase

> A Splitwise-style expense sharing app. Track shared costs with roommates, travel companions, or any group — and settle up with one tap.

<!-- Replace with a real screenshot once the UI is built -->
![App screenshot placeholder](https://via.placeholder.com/1200x630/1a1a2e/ffffff?text=SplitEase+Screenshot)

---

## Features

- **Group management** – Create groups for apartments, trips, or any shared purpose
- **Flexible expense splitting** – Split equally, by exact amounts, or by percentage
- **Debt simplification** – Smart algorithm reduces N debts to the minimum number of payments needed
- **Settlement tracking** – Record payments between members and watch balances update in real time
- **Email notifications** – Get notified when someone adds an expense or records a payment
- **Push notifications** – Real-time browser notifications via Web Push (PWA)
- **Offline support** – View your groups and expenses without internet; create expenses in the background
- **Installable PWA** – Add to home screen on iOS and Android
- **Full REST API** – Swagger UI available at `/docs` on every service

---

## Quick Start (Local Development)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/splitease.git
cd splitease

# 2. One command to do everything
make dev-setup
```

That's it. `make dev-setup` will:

- Copy `.env.example` → `.env`
- Build all Docker images
- Start all services (Postgres, Redis, 4 backend services, React frontend)
- Run database migrations
- Seed the database with test users and sample expenses

Then open http://localhost:3000 and log in with:

| Email | Password |
|-------|----------|
| `alice@test.com` | `password123` |
| `bob@test.com` | `password123` |
| `charlie@test.com` | `password123` |

### Common dev commands

```bash
make up           # Start services
make down         # Stop services
make logs         # Tail all logs
make migrate      # Run database migrations
make seed         # Re-seed the database
make shell-db     # Open psql
make shell-auth   # Open bash in auth-service
make help         # List all available commands
```

---

## Architecture Overview

SplitEase uses a microservices architecture with 4 backend services, a shared PostgreSQL database, and a React SPA deployed as a PWA.

```
Browser ──HTTPS──► CloudFront ──► S3 (React SPA)
           │
           └──/api/*──► ALB ──► API Gateway (8000)
                                    ├──/auth/*──► Auth Service (8001) ──► PostgreSQL (auth_schema)
                                    │                                  ──► Redis
                                    └──/expenses/*──► Expense Service (8002) ──► PostgreSQL (expenses_schema)

                         Notification Worker (headless) ──► PostgreSQL ──► SMTP / Web Push
```

See [docs/architecture.md](docs/architecture.md) for:
- Full Mermaid system diagram
- Service responsibility breakdown
- Data flow sequences (login, create expense, settle debt)
- Database ER diagram
- API Gateway routing table
- PWA offline strategy
- AWS deployment diagram
- Cost estimates and design decisions

---

## Tech Stack

### Backend

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| HTTP Framework | FastAPI |
| Database ORM | SQLAlchemy 2 (async) |
| DB Driver | asyncpg |
| Migrations | Alembic |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Cache / Rate-limiting | Redis (aioredis) |
| Email | aiosmtplib |
| Push Notifications | pywebpush (VAPID) |

### Frontend

| Layer | Technology |
|-------|-----------|
| Framework | React 18 |
| Build tool | Vite |
| Language | TypeScript |
| Styling | Tailwind CSS |
| State | Zustand |
| HTTP Client | TanStack Query + Axios |
| Forms | React Hook Form + Zod |
| PWA | Vite PWA Plugin (Workbox) |

### Infrastructure

| Layer | Technology |
|-------|-----------|
| Containers | Docker + Docker Compose (dev) |
| Orchestration | AWS ECS Fargate |
| Database | AWS RDS PostgreSQL 16 |
| Cache | AWS ElastiCache Redis 7 |
| Frontend CDN | AWS S3 + CloudFront |
| Registry | AWS ECR |
| IaC | Terraform 1.5+ |
| CI/CD | GitHub Actions (OIDC – no long-lived secrets) |

---

## API Endpoints Summary

The API is exposed through the gateway at `:8000`. Swagger UI is available at
`http://localhost:8000/docs` during development.

### Auth (`/api/auth`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Create a new account |
| POST | `/api/auth/login` | Login and receive tokens |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/logout` | Revoke refresh token |
| POST | `/api/auth/forgot-password` | Send password reset email |
| POST | `/api/auth/reset-password` | Apply new password |

### Users (`/api/users`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/users/me` | Get current user profile |
| PATCH | `/api/users/me` | Update profile |
| POST | `/api/users/me/push-subscription` | Register web push subscription |

### Groups (`/api/groups`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/groups` | List my groups |
| POST | `/api/groups` | Create group |
| GET | `/api/groups/{id}` | Get group details |
| PATCH | `/api/groups/{id}` | Update group |
| POST | `/api/groups/{id}/members` | Add member |
| DELETE | `/api/groups/{id}/members/{uid}` | Remove member |
| GET | `/api/groups/{id}/balances` | Get simplified debt graph |

### Expenses (`/api/expenses`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/expenses` | List expenses (paginated, filter by group) |
| POST | `/api/expenses` | Create expense |
| GET | `/api/expenses/{id}` | Get expense detail |
| PATCH | `/api/expenses/{id}` | Update expense |
| DELETE | `/api/expenses/{id}` | Soft-delete expense |

### Settlements (`/api/settlements`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/settlements` | Record a payment |
| GET | `/api/groups/{id}/settlements` | List settlements in group |

---

## Deployment Guide

See [docs/deployment.md](docs/deployment.md) for the full guide. Here is the summary:

### First-time AWS deployment

```bash
# 1. Create AWS infrastructure with Terraform
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
terraform init && terraform apply

# 2. Set GitHub repository secrets/variables (from Terraform outputs)
#    Secrets: AWS_DEPLOY_ROLE_ARN
#    Variables: AWS_REGION, ECR_REGISTRY, S3_BUCKET, CLOUDFRONT_DISTRIBUTION_ID, API_URL

# 3. Push to main to trigger the deploy pipeline
git push origin main
```

### Subsequent deployments

Just push to `main`. GitHub Actions will:

1. Build and push Docker images to ECR (parallel per service)
2. Build the React SPA and deploy to S3 + invalidate CloudFront
3. Register new ECS task definitions and update each service
4. Run a smoke test to confirm health

---

## Project Structure

```
splitease/
├── apps/
│   └── web/                    # React + Vite frontend (TypeScript)
├── services/
│   ├── api-gateway/            # FastAPI gateway – routing + rate limiting
│   ├── auth-service/           # FastAPI – user auth, JWT, email, push subs
│   ├── expense-service/        # FastAPI – groups, expenses, settlements
│   └── notification-worker/    # Async polling worker – email + web push
├── infrastructure/
│   └── terraform/              # All AWS infrastructure as code
│       ├── main.tf             # Provider + locals
│       ├── vpc.tf              # VPC, subnets, security groups
│       ├── ecr.tf              # Container registries
│       ├── rds.tf              # PostgreSQL on RDS
│       ├── elasticache.tf      # Redis on ElastiCache
│       ├── ecs.tf              # ECS cluster, task definitions, services
│       ├── s3_cloudfront.tf    # Frontend hosting
│       ├── variables.tf        # Input variables
│       └── outputs.tf          # Output values
├── .github/
│   └── workflows/
│       ├── ci.yml              # Lint, test, build on every push
│       └── deploy.yml          # Build images + deploy to AWS on main
├── scripts/
│   ├── init-db.sql             # Database schema initialisation
│   └── seed.py                 # Test data seeder
├── docs/
│   ├── architecture.md         # System design + diagrams
│   └── deployment.md           # Deployment guide
├── docker-compose.yml          # Local development stack
├── Makefile                    # Developer shortcuts
├── .env.example                # Environment variable template
└── README.md                   # This file
```

---

## Contributing

Contributions are welcome. Please follow these guidelines:

### Development workflow

1. Fork the repository and create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Make your changes. Ensure:
   - Python code follows PEP 8 (enforced by `ruff`)
   - TypeScript code passes ESLint (`make lint-web`)
   - New Python functions have type hints
   - New API endpoints have Pydantic schemas

3. Write or update tests.

4. Run the full CI check locally:
   ```bash
   make test           # Python tests
   make lint-web       # Frontend lint
   make type-check     # TypeScript
   ```

5. Commit with a descriptive message:
   ```bash
   git commit -m "feat(expenses): add percentage-based split type"
   ```
   We follow [Conventional Commits](https://www.conventionalcommits.org/).

6. Open a pull request against `main`.

### Branch naming

| Prefix | Use for |
|--------|---------|
| `feature/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation only |
| `refactor/` | Code cleanup, no feature change |
| `infra/` | Infrastructure / Terraform changes |

### Commit message format

```
type(scope): short description

Optional longer description explaining why, not what.
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `infra`

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

```
MIT License

Copyright (c) 2024 SplitEase Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
