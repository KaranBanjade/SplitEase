#!/usr/bin/env bash
# demo-docker.sh — Before-vs-After: manual setup vs Docker Compose
# Demonstrates how containerisation resolves deployment complexity.
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
DIM='\033[2m'

step()    { echo -e "\n${BOLD}${CYAN}━━━ $* ━━━${RESET}"; }
info()    { echo -e "  ${CYAN}$*${RESET}"; }
success() { echo -e "  ${GREEN}✔  $*${RESET}"; }
warn()    { echo -e "  ${YELLOW}⚠  $*${RESET}"; }
bad()     { echo -e "  ${RED}✘  $*${RESET}"; }

echo -e "\n${BOLD}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║  SplitEase — Docker Before-vs-After Demo         ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${RESET}"

# ─── BEFORE ───────────────────────────────────────────────────────────────────
step "BEFORE — Deploying manually (without Docker)"

echo -e "\n  ${BOLD}What a developer would have to do on a fresh machine:${RESET}\n"

echo -e "  ${RED}1. Install system dependencies manually${RESET}"
echo -e "${DIM}     brew install python@3.11 postgresql redis node
     # (exact versions must match — mismatches cause subtle bugs)${RESET}"
echo ""

echo -e "  ${RED}2. Create and activate 4 separate virtual environments${RESET}"
echo -e "${DIM}     cd services/api-gateway   && python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
     cd services/auth-service   && python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
     cd services/expense-service && python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
     cd services/notification-worker && python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
     cd web && npm install${RESET}"
echo ""

echo -e "  ${RED}3. Start infrastructure services${RESET}"
echo -e "${DIM}     brew services start postgresql
     brew services start redis
     createdb splitease_auth
     createdb splitease_expense
     # Remember to set passwords, roles, permissions…${RESET}"
echo ""

echo -e "  ${RED}4. Set environment variables for every service${RESET}"
echo -e "${DIM}     export DATABASE_URL=postgresql+asyncpg://user:pass@localhost/splitease_auth
     export REDIS_URL=redis://localhost:6379
     export AUTH_SERVICE_URL=http://localhost:8001
     export EXPENSE_SERVICE_URL=http://localhost:8002
     export SECRET_KEY=dev-secret-key
     # ... repeated for all 4 services, each in a different terminal tab${RESET}"
echo ""

echo -e "  ${RED}5. Run database migrations manually${RESET}"
echo -e "${DIM}     cd services/auth-service    && alembic upgrade head
     cd services/expense-service && alembic upgrade head${RESET}"
echo ""

echo -e "  ${RED}6. Start each service in a separate terminal${RESET}"
echo -e "${DIM}     # Terminal 1:
     cd services/api-gateway && source .venv/bin/activate && uvicorn main:app --port 8000
     # Terminal 2:
     cd services/auth-service && source .venv/bin/activate && uvicorn main:app --port 8001
     # Terminal 3:
     cd services/expense-service && source .venv/bin/activate && uvicorn main:app --port 8002
     # Terminal 4:
     cd services/notification-worker && source .venv/bin/activate && python -m app.main
     # Terminal 5:
     cd web && npm run dev${RESET}"
echo ""

echo -e "  ${RED}Problems with manual setup:${RESET}"
bad "Python version mismatches break packages"
bad "Different OS (macOS vs Linux) gives different behaviour"
bad "5+ terminals needed, each must be started in order"
bad "Manual env vars — easy to miss one, causes cryptic errors"
bad "Database setup differs between developers"
bad "No isolation — a dependency upgrade in one service can break others"
bad "New team member onboarding takes hours"
echo ""

# ─── AFTER ────────────────────────────────────────────────────────────────────
step "AFTER — Deploying with Docker Compose"

echo -e "\n  ${BOLD}What a developer actually does with Docker:${RESET}\n"
echo -e "  ${GREEN}One command:${RESET}"
echo -e "\n    ${BOLD}./start.sh${RESET}\n"
echo -e "  That's it.\n"

echo -e "  ${GREEN}What Docker does under the hood:${RESET}"
success "Builds an identical Linux container for every service"
success "Installs exact pinned dependencies in each isolated image"
success "Starts PostgreSQL + Redis with health-checks (services wait for them)"
success "Runs database migrations inside the container automatically"
success "Wires all environment variables via docker-compose.yml"
success "Every developer gets byte-for-byte the same environment"
success "Works on macOS, Linux, Windows — no OS-specific differences"
echo ""

# ─── LIVE PROOF ───────────────────────────────────────────────────────────────
step "LIVE — Showing running Docker containers"

if ! docker info &>/dev/null 2>&1; then
  warn "Docker not running — skipping live section."
else
  echo ""
  docker compose ps --format "table {{.Name}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null \
    || docker compose ps
  echo ""
  info "All services running in isolated containers, started with one command."

  step "LIVE — Container isolation: each service has its own filesystem"
  echo ""
  echo -e "  ${BOLD}api-gateway Python version:${RESET}"
  docker compose exec api-gateway python3 --version 2>/dev/null || warn "api-gateway not running"

  echo -e "\n  ${BOLD}auth-service Python version:${RESET}"
  docker compose exec auth-service python3 --version 2>/dev/null || warn "auth-service not running"

  echo -e "\n  ${BOLD}Installed packages in api-gateway (first 8):${RESET}"
  docker compose exec api-gateway pip list --format=columns 2>/dev/null | head -9 || true

  step "LIVE — Each service has its own isolated database"
  echo ""
  info "auth-service database (splitease_auth):"
  docker compose exec db psql -U splitease -d splitease_auth \
    -c "\dt" 2>/dev/null || warn "DB not reachable"

  echo ""
  info "expense-service database (splitease_expenses):"
  docker compose exec db psql -U splitease -d splitease_expenses \
    -c "\dt" 2>/dev/null || warn "DB not reachable"

  step "LIVE — Health endpoints confirm all services are up"
  echo ""
  for svc_url in \
    "api-gateway|http://localhost:8000/health" \
    "auth-service|http://localhost:8001/health" \
    "expense-service|http://localhost:8002/health"; do
    name="${svc_url%%|*}"
    url="${svc_url##*|}"
    response=$(curl -sf "$url" 2>/dev/null) && \
      echo -e "  ${GREEN}✔${RESET}  ${BOLD}$name${RESET} → $response" || \
      echo -e "  ${RED}✘${RESET}  ${BOLD}$name${RESET} → not responding"
  done
fi

# ─── Summary ──────────────────────────────────────────────────────────────────
step "SUMMARY"
echo ""
echo -e "  ${BOLD}Without Docker${RESET}                     ${BOLD}With Docker${RESET}"
echo -e "  ${RED}~45 min setup on fresh machine${RESET}      ${GREEN}./start.sh  (~2 min)${RESET}"
echo -e "  ${RED}5+ manual terminal tabs${RESET}             ${GREEN}Single command${RESET}"
echo -e "  ${RED}OS-specific behaviour${RESET}               ${GREEN}Identical across macOS / Linux / Windows${RESET}"
echo -e "  ${RED}Manual env vars, easy to miss one${RESET}   ${GREEN}Declared once in docker-compose.yml${RESET}"
echo -e "  ${RED}Dependency conflicts between services${RESET} ${GREEN}Full isolation per container${RESET}"
echo -e "  ${RED}Hard to reproduce bugs${RESET}              ${GREEN}\"Works on my machine\" = works everywhere${RESET}"
echo ""
echo -e "${BOLD}${GREEN}Docker demo complete.${RESET}\n"
