#!/usr/bin/env bash
# demo-circuit-breaker.sh — demonstrates the full circuit breaker lifecycle
set -euo pipefail

# ─── colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

step()    { echo -e "\n${BOLD}${CYAN}━━━ $* ━━━${RESET}"; }
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }

GATEWAY="http://localhost:8000"
AUTH_CONTAINER="collegeproject-auth-service-1"

echo -e "\n${BOLD}╔══════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║     SplitEase — Circuit Breaker Demo         ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${RESET}"

# ─── helper: pretty-print breaker state ───────────────────────────────────────
show_breakers() {
  local raw
  raw=$(curl -s "$GATEWAY/health/breakers")
  local auth_state auth_count exp_state exp_count
  auth_state=$(echo "$raw" | python3 -c "import sys,json; print(json.load(sys.stdin)['auth-service']['state'])")
  auth_count=$(echo "$raw" | python3 -c "import sys,json; print(json.load(sys.stdin)['auth-service']['fail_counter'])")
  exp_state=$(echo  "$raw" | python3 -c "import sys,json; print(json.load(sys.stdin)['expense-service']['state'])")

  # colour the state
  colour_state() {
    case "$1" in
      closed)    echo -e "${GREEN}$1${RESET}" ;;
      open)      echo -e "${RED}$1${RESET}" ;;
      half-open) echo -e "${YELLOW}$1${RESET}" ;;
      *)         echo "$1" ;;
    esac
  }

  echo -e "  auth-service    → state: $(colour_state "$auth_state")  fail_counter: ${BOLD}$auth_count${RESET}"
  echo -e "  expense-service → state: $(colour_state "$exp_state")"
}

# ─── Step 1: baseline ─────────────────────────────────────────────────────────
step "STEP 1 — Baseline (both breakers closed)"
show_breakers

# ─── Step 2: take down auth-service ───────────────────────────────────────────
step "STEP 2 — Stopping auth-service (simulates outage)"
docker stop "$AUTH_CONTAINER" > /dev/null
success "auth-service stopped."

# ─── Step 3: send requests and watch breaker trip ─────────────────────────────
step "STEP 3 — Sending 4 requests (breaker trips on 3rd failure)"
for i in 1 2 3 4; do
  response=$(curl -s "$GATEWAY/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"demo@test.com","password":"password123"}')
  detail=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('detail','?'))" 2>/dev/null || echo "$response")
  if echo "$detail" | grep -q "circuit open"; then
    echo -e "  Request $i → ${RED}$detail${RESET}  ← BREAKER OPEN"
  else
    echo -e "  Request $i → ${YELLOW}$detail${RESET}"
  fi
done

step "STEP 4 — Breaker state (should be OPEN)"
show_breakers

# ─── Step 5: restore auth-service ─────────────────────────────────────────────
step "STEP 5 — Restarting auth-service"
docker start "$AUTH_CONTAINER" > /dev/null
success "auth-service restarted."

# ─── Step 6: wait for reset_timeout ───────────────────────────────────────────
RESET_TIMEOUT=30
step "STEP 6 — Waiting ${RESET_TIMEOUT}s for breaker reset_timeout (→ HALF-OPEN)"
for i in $(seq "$RESET_TIMEOUT" -1 1); do
  echo -ne "  ${CYAN}$i seconds remaining...${RESET}\r"
  sleep 1
done
echo -ne "\033[2K"
show_breakers

# ─── Step 7: probe through HALF-OPEN ──────────────────────────────────────────
step "STEP 7 — Sending one probe request (breaker is HALF-OPEN)"
response=$(curl -s "$GATEWAY/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@test.com","password":"password123"}')
detail=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('detail','?'))" 2>/dev/null || echo "$response")
echo -e "  Probe response → ${GREEN}$detail${RESET}"
info "(auth-service responded → breaker closes)"

# ─── Step 8: final state ──────────────────────────────────────────────────────
step "STEP 8 — Final breaker state (should be CLOSED)"
show_breakers

echo -e "\n${BOLD}${GREEN}Demo complete.${RESET}"
echo -e "  CLOSED → OPEN (3 failures) → HALF-OPEN (30s) → CLOSED (1 success)\n"
