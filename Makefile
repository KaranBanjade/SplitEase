.PHONY: up up-build down down-v logs logs-auth logs-expense logs-gateway \
        build shell-auth shell-expense shell-db \
        migrate-auth migrate-expense migrate \
        seed \
        test-auth test-expense \
        lint-web lint-web-fix type-check \
        install-web build-web \
        clean generate-vapid generate-secret dev-setup help

# Terminal colors (safe fallback if tput not available)
GREEN  := $(shell tput -Txterm setaf 2 2>/dev/null || echo "")
YELLOW := $(shell tput -Txterm setaf 3 2>/dev/null || echo "")
RESET  := $(shell tput -Txterm sgr0 2>/dev/null || echo "")

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(RESET) %s\n", $$1, $$2}'

# ─────────────────────────────────────────────────────────────────────────────
# Docker Compose lifecycle
# ─────────────────────────────────────────────────────────────────────────────

up: ## Start all services (detached)
	docker compose up -d
	@echo "$(GREEN)Services starting..."
	@echo "  Frontend  → http://localhost:3000"
	@echo "  Gateway   → http://localhost:8000"
	@echo "  Auth      → http://localhost:8001"
	@echo "  Expense   → http://localhost:8002$(RESET)"

up-build: ## Build images then start all services (detached)
	docker compose up -d --build

down: ## Stop all services
	docker compose down

down-v: ## Stop all services and delete volumes  [DESTRUCTIVE – erases DB data]
	@echo "$(YELLOW)WARNING: This will delete all database data. Press Ctrl-C to abort.$(RESET)"
	@sleep 3
	docker compose down -v

build: ## (Re)build all Docker images
	docker compose build

# ─────────────────────────────────────────────────────────────────────────────
# Logs
# ─────────────────────────────────────────────────────────────────────────────

logs: ## Tail all service logs
	docker compose logs -f

logs-auth: ## Tail auth-service logs
	docker compose logs -f auth-service

logs-expense: ## Tail expense-service logs
	docker compose logs -f expense-service

logs-gateway: ## Tail api-gateway logs
	docker compose logs -f api-gateway

logs-worker: ## Tail notification-worker logs
	docker compose logs -f notification-worker

logs-web: ## Tail frontend logs
	docker compose logs -f web

# ─────────────────────────────────────────────────────────────────────────────
# Shells
# ─────────────────────────────────────────────────────────────────────────────

shell-auth: ## Open a bash shell inside the auth-service container
	docker compose exec auth-service /bin/bash

shell-expense: ## Open a bash shell inside the expense-service container
	docker compose exec expense-service /bin/bash

shell-gateway: ## Open a bash shell inside the api-gateway container
	docker compose exec api-gateway /bin/bash

shell-db: ## Open a psql shell connected to the splitease database
	docker compose exec postgres psql -U splitease splitease

shell-redis: ## Open a redis-cli session
	docker compose exec redis redis-cli

# ─────────────────────────────────────────────────────────────────────────────
# Database migrations (Alembic)
# ─────────────────────────────────────────────────────────────────────────────

migrate-auth: ## Run auth-service Alembic migrations to HEAD
	docker compose exec auth-service alembic upgrade head

migrate-expense: ## Run expense-service Alembic migrations to HEAD
	docker compose exec expense-service alembic upgrade head

migrate: migrate-auth migrate-expense ## Run ALL service migrations

# ─────────────────────────────────────────────────────────────────────────────
# Database seeding
# ─────────────────────────────────────────────────────────────────────────────

seed: ## Seed the database with test users, groups, and expenses
	@docker compose exec -T postgres psql -U splitease -c "SELECT 1" > /dev/null 2>&1 \
		|| (echo "$(YELLOW)Database not ready – start services first: make up$(RESET)" && exit 1)
	DATABASE_URL=postgresql+asyncpg://splitease:password@localhost:5432/splitease \
		python scripts/seed.py

# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

test-auth: ## Run auth-service test suite
	docker compose exec auth-service pytest tests/ -v

test-expense: ## Run expense-service test suite
	docker compose exec expense-service pytest tests/ -v

test: test-auth test-expense ## Run ALL tests

# ─────────────────────────────────────────────────────────────────────────────
# Frontend (apps/web)
# ─────────────────────────────────────────────────────────────────────────────

install-web: ## Install frontend npm dependencies
	cd apps/web && npm install

lint-web: ## ESLint check on frontend source
	cd apps/web && npm run lint

lint-web-fix: ## ESLint auto-fix on frontend source
	cd apps/web && npm run lint -- --fix

type-check: ## TypeScript type check (no emit)
	cd apps/web && npm run type-check

build-web: ## Build frontend for production (outputs to apps/web/dist/)
	cd apps/web && npm run build

preview-web: ## Preview the production build locally
	cd apps/web && npm run preview

# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

generate-vapid: ## Generate VAPID key pair for Web Push notifications
	@command -v npx >/dev/null 2>&1 || (echo "npx not found – install Node.js first" && exit 1)
	npx web-push generate-vapid-keys

generate-secret: ## Generate a cryptographically secure SECRET_KEY (256-bit hex)
	@openssl rand -hex 32

clean: ## Remove build artefacts, Python caches, and Vite cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf apps/web/dist apps/web/node_modules/.vite 2>/dev/null || true
	@echo "$(GREEN)Clean complete$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# First-time developer setup
# ─────────────────────────────────────────────────────────────────────────────

dev-setup: ## Complete first-time setup: env file → build → start → migrate → seed
	@echo "$(YELLOW)Step 1/5  Checking .env file...$(RESET)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)  Created .env from .env.example$(RESET)"; \
		echo "$(YELLOW)  Review .env and update SECRET_KEY before continuing.$(RESET)"; \
	else \
		echo "  .env already exists – skipping copy"; \
	fi
	@echo "$(YELLOW)Step 2/5  Building and starting services...$(RESET)"
	$(MAKE) up-build
	@echo "$(YELLOW)Step 3/5  Waiting for services to be healthy...$(RESET)"
	@sleep 15
	@echo "$(YELLOW)Step 4/5  Running database migrations...$(RESET)"
	$(MAKE) migrate
	@echo "$(YELLOW)Step 5/5  Seeding database with test data...$(RESET)"
	$(MAKE) seed
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@echo "$(GREEN) Setup complete!$(RESET)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@echo ""
	@echo "  App       → $(GREEN)http://localhost:3000$(RESET)"
	@echo "  API Docs  → $(GREEN)http://localhost:8000/docs$(RESET)"
	@echo ""
	@echo "  Test accounts (password: password123):"
	@echo "    $(YELLOW)alice@test.com$(RESET)"
	@echo "    $(YELLOW)bob@test.com$(RESET)"
	@echo "    $(YELLOW)charlie@test.com$(RESET)"
