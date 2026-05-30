# Contributing to SplitEase

Thank you for your interest in contributing! This guide covers everything you need to get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Branch Naming](#branch-naming)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold its standards. Please report unacceptable behavior to the maintainers.

---

## Getting Started

### Prerequisites

- **Docker** and **Docker Compose** (for running the full stack)
- **Python 3.12+** (for running individual services or scripts)
- **Node.js 20+** and **npm** (for the React frontend)
- **Make** (for convenience commands)

### Local setup

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/<your-username>/SplitEase.git
cd SplitEase

# 2. One command spins everything up
make dev-setup
```

`make dev-setup` will:
- Copy `.env.example` → `.env`
- Build all Docker images
- Start all services (Postgres, Redis, 4 backend services, React frontend)
- Run database migrations
- Seed the database with test data

Then open <http://localhost:3000> and log in with:

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
make test         # Run Python tests
make lint-web     # Frontend ESLint
make type-check   # TypeScript check
make help         # List all available commands
```

---

## Development Workflow

1. **Sync your fork** with `upstream` before starting:
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create a feature branch** off `main`:
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Make your changes** following the coding standards below.

4. **Write or update tests** for any changed logic.

5. **Run the full CI check locally** before opening a PR:
   ```bash
   make test           # Python unit/integration tests
   make lint-web       # Frontend ESLint
   make type-check     # TypeScript type check
   ```

6. **Commit** with a descriptive message (see [Commit Messages](#commit-messages)).

7. **Push** your branch and open a pull request against `main`.

---

## Project Structure

```
SplitEase/
├── apps/
│   └── web/                    # React + Vite frontend (TypeScript)
├── services/
│   ├── api-gateway/            # FastAPI gateway – routing + rate limiting
│   ├── auth-service/           # FastAPI – user auth, JWT, email, push subs
│   ├── expense-service/        # FastAPI – groups, expenses, settlements
│   └── notification-worker/    # Async polling worker – email + web push
├── infrastructure/
│   └── terraform/              # AWS infrastructure as code
├── .github/
│   └── workflows/              # CI and deploy pipelines
├── scripts/                    # DB init and seeder
├── docs/                       # Architecture and deployment docs
├── docker-compose.yml          # Local development stack
└── Makefile                    # Developer shortcuts
```

---

## Coding Standards

### Python (backend services)

- Follow **PEP 8** — enforced by [`ruff`](https://docs.astral.sh/ruff/)
- Use **type hints** on all function signatures
- Use **Pydantic schemas** for all request/response models
- Write **async** functions for I/O-bound operations (SQLAlchemy 2 async, aiosmtplib, etc.)

### TypeScript (frontend)

- Follow the existing ESLint config (`apps/web/.eslintrc.*`)
- Use **Zod** for runtime validation at API boundaries
- Prefer **React Hook Form** for forms
- Keep components small — extract hooks for non-trivial state logic

### General

- No commented-out code in PRs
- No `TODO` comments without a linked issue
- Keep pull requests focused — one concern per PR

---

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short description

Optional longer description explaining WHY, not WHAT.
```

| Type | When to use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code cleanup, no feature change |
| `test` | Adding or fixing tests |
| `chore` | Tooling, deps, config |
| `infra` | Terraform / infrastructure changes |

**Examples:**
```
feat(expenses): add percentage-based split type
fix(auth): handle refresh token rotation race condition
docs(deployment): update Terraform first-deploy steps
```

---

## Pull Request Process

1. Fill in the PR template fully.
2. Ensure all CI checks pass (`ci.yml`).
3. Request a review from at least one maintainer.
4. Address review feedback; don't force-push after a review starts (use new commits).
5. A maintainer will squash-merge once approved.

---

## Branch Naming

| Prefix | Use for |
|--------|---------|
| `feature/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation only |
| `refactor/` | Code cleanup |
| `infra/` | Infrastructure / Terraform changes |

---

## Reporting Bugs

Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) issue template. Include:

- Steps to reproduce
- Expected vs. actual behaviour
- Browser / OS / Docker version (if relevant)
- Any relevant logs (`make logs`)

---

## Suggesting Features

Use the [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md) issue template. Describe the problem you're solving, not just the solution.

---

## Security Issues

**Do not open public issues for security vulnerabilities.** See [SECURITY.md](SECURITY.md) for the responsible disclosure process.
