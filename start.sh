#!/usr/bin/env bash
# start.sh — failproof local dev launcher for SplitEase
#
# Usage:
#   ./start.sh            — start (or resume) all services
#   ./start.sh --build    — force rebuild all Docker images first
#   ./start.sh --fresh    — wipe database volumes, then start clean
#   ./start.sh --down     — stop and remove all containers
#   ./start.sh --logs     — tail logs of all running services
#
# Works with: Docker Desktop, Colima (default), OrbStack
# Requires:   bash 3.2+, curl, lsof  (all pre-installed on macOS)

set -euo pipefail
IFS=$'\n\t'

# ── colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()    { echo -e "${CYAN}▸${RESET} $*"; }
success() { echo -e "${GREEN}✔${RESET} $*"; }
warn()    { echo -e "${YELLOW}⚠${RESET}  $*"; }
die()     { echo -e "${RED}✘${RESET} $*" >&2; exit 1; }
step()    { echo ""; echo -e "${BOLD}── $* ──${RESET}"; }

# ── parse flags ───────────────────────────────────────────────────────────────
DO_BUILD=false; DO_FRESH=false; DO_DOWN=false; DO_LOGS=false
for arg in "$@"; do
  case "$arg" in
    --build) DO_BUILD=true ;;
    --fresh) DO_FRESH=true ;;
    --down)  DO_DOWN=true  ;;
    --logs)  DO_LOGS=true  ;;
    *) die "Unknown flag: $arg\nUsage: $0 [--build] [--fresh] [--down] [--logs]" ;;
  esac
done

# ── locate project root ───────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║      SplitEase — Local Dev Launcher      ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

# ── Step 1: find & expose Docker socket ──────────────────────────────────────
step "Docker runtime"

_try_socket() {
  local sock="$1"
  DOCKER_HOST="unix://$sock" docker info &>/dev/null 2>&1 && echo "$sock"
}

find_docker_socket() {
  # Check explicit DOCKER_HOST first
  if [[ -n "${DOCKER_HOST:-}" ]]; then
    local sock="${DOCKER_HOST#unix://}"
    if [[ -S "$sock" ]]; then
      echo "$sock"; return 0
    fi
  fi

  # Well-known socket locations (checked in priority order)
  local candidates=(
    "/var/run/docker.sock"                                  # Docker Desktop / standard Linux
    "$HOME/.colima/default/docker.sock"                     # Colima default profile
    "$HOME/.colima/docker.sock"                             # Colima older layout
    "/Users/$USER/.colima/default/docker.sock"              # Colima explicit user path
    "$HOME/.orbstack/run/docker.sock"                       # OrbStack
    "/run/user/$(id -u)/docker.sock"                        # rootless Docker on Linux
  )

  for s in "${candidates[@]}"; do
    [[ -S "$s" ]] || continue
    local result
    result=$(_try_socket "$s") && { echo "$result"; return 0; } || true
  done
  return 1
}

_start_colima() {
  info "Starting Colima…"
  colima start --runtime docker 2>&1 | grep -v "^$" | sed 's/^/  /' || true

  # Wait up to 30 s for the socket to appear
  local waited=0
  while [[ $waited -lt 30 ]]; do
    sleep 2; waited=$((waited + 2))
    local sock="$HOME/.colima/default/docker.sock"
    if [[ -S "$sock" ]]; then
      DOCKER_HOST="unix://$sock" docker info &>/dev/null && return 0
    fi
  done
  return 1
}

# Try to find a working socket; if none, attempt to start Colima
DOCKER_SOCK=""
DOCKER_SOCK=$(find_docker_socket) || true

if [[ -z "$DOCKER_SOCK" ]]; then
  if command -v colima &>/dev/null; then
    warn "Docker socket not found — attempting to start Colima…"
    _start_colima || die \
      "Could not start Colima.\n  Run: colima start\n  Or start Docker Desktop manually."
    DOCKER_SOCK=$(find_docker_socket) || die \
      "Colima started but no Docker socket found. Check: colima status"
  else
    die "Docker is not running and Colima is not installed.\n\
  • Install Docker Desktop: https://www.docker.com/products/docker-desktop/\n\
  • Or install Colima:       brew install colima"
  fi
fi

export DOCKER_HOST="unix://$DOCKER_SOCK"
success "Docker socket: $DOCKER_SOCK"

# ── Step 2: ensure docker compose plugin ─────────────────────────────────────
step "docker compose"

if ! docker compose version &>/dev/null 2>&1; then
  warn "docker compose plugin not found — attempting to install via Homebrew…"
  command -v brew &>/dev/null || die \
    "Homebrew not found. Install docker-compose manually:\n  https://docs.docker.com/compose/install/"
  brew install docker-compose

  # Register the plugin dir in Docker config so the CLI finds it
  for brew_prefix in /opt/homebrew /usr/local; do
    local_plugin="$brew_prefix/lib/docker/cli-plugins/docker-compose"
    [[ -f "$local_plugin" ]] || continue
    plugin_dir="$(dirname "$local_plugin")"
    cfg="$HOME/.docker/config.json"
    mkdir -p "$HOME/.docker"
    [[ -f "$cfg" ]] || echo '{}' > "$cfg"
    python3 - "$plugin_dir" "$cfg" <<'PY'
import sys, json
d, cfg = sys.argv[1], sys.argv[2]
with open(cfg) as f: data = json.load(f)
dirs = data.get("cliPluginsExtraDirs", [])
if d not in dirs:
    dirs.append(d)
    data["cliPluginsExtraDirs"] = dirs
    with open(cfg, "w") as f: json.dump(data, f, indent=2)
PY
    break
  done

  docker compose version &>/dev/null 2>&1 || die \
    "docker compose still unavailable after install. Restart your terminal and retry."
fi
success "docker compose $(docker compose version --short 2>/dev/null || echo 'ok')"

# ── Step 3: --down shortcut ───────────────────────────────────────────────────
if [[ "$DO_DOWN" == true ]]; then
  step "Stopping services"
  docker compose down --remove-orphans
  success "All containers stopped."
  exit 0
fi

# ── Step 4: --logs shortcut ───────────────────────────────────────────────────
if [[ "$DO_LOGS" == true ]]; then
  exec docker compose logs -f --tail=100
fi

# ── Step 5: release ports that would block us ────────────────────────────────
step "Port check (3000 8000 8001 8002)"

kill_port() {
  local port="$1"
  # lsof -ti returns PIDs; ignore errors if nothing is listening
  local pids
  pids=$(lsof -ti :"$port" 2>/dev/null || true)
  [[ -z "$pids" ]] && return 0
  for pid in $pids; do
    local cmd
    cmd=$(ps -p "$pid" -o comm= 2>/dev/null || echo "?")
    # Only evict stray dev servers / port-forwards — never kill Docker daemons
    if echo "$cmd" | grep -qiE "uvicorn|python|node|kubectl|vite"; then
      warn "Releasing port $port — killing '$cmd' (PID $pid)"
      kill "$pid" 2>/dev/null || true
    fi
  done
}

for p in 3000 8000 8001 8002; do kill_port "$p"; done
sleep 1
success "Ports clear."

# ── Step 6: fresh wipe (optional) ─────────────────────────────────────────────
if [[ "$DO_FRESH" == true ]]; then
  step "Fresh start — wiping volumes"
  warn "All database data will be deleted."
  docker compose down -v --remove-orphans 2>/dev/null || true
  success "Volumes removed."
fi

# ── Step 7: build / pull / start ──────────────────────────────────────────────
step "Starting services"

compose_args=("-d" "--remove-orphans")
[[ "$DO_BUILD" == true ]] && compose_args+=("--build")

docker compose up "${compose_args[@]}"

# ── Step 8: health checks ─────────────────────────────────────────────────────
step "Waiting for services"

# Wait for a container's Docker-native healthcheck to reach 'healthy' or 'running'
wait_container() {
  local name="$1" max="${2:-90}" elapsed=0 interval=3
  while true; do
    local status
    status=$(docker inspect --format='{{.State.Status}}' "$name" 2>/dev/null || echo "missing")
    local health
    health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{end}}' \
             "$name" 2>/dev/null || echo "")

    # Accept: running with no healthcheck, or healthy
    if [[ "$status" == "running" && ( -z "$health" || "$health" == "healthy" ) ]]; then
      success "$name  ${health:+(healthy)}"
      return 0
    fi
    if [[ "$status" == "exited" || "$status" == "dead" ]]; then
      warn "$name exited unexpectedly. Showing last 30 lines of logs:"
      docker logs --tail 30 "$name" 2>&1 | sed 's/^/  /'
      return 1
    fi
    if [[ $elapsed -ge $max ]]; then
      warn "$name not healthy after ${max}s. Check: docker compose logs $name"
      return 1
    fi
    printf "\r  ${CYAN}%-45s${RESET} %ds" "Waiting for $name…" "$elapsed"
    sleep "$interval"; elapsed=$((elapsed + interval))
  done
}

# Wait for HTTP endpoints (for services without a Docker healthcheck)
wait_http() {
  local label="$1" url="$2" max="${3:-120}" elapsed=0 interval=3
  while ! curl -sf --max-time 3 "$url" &>/dev/null; do
    if [[ $elapsed -ge $max ]]; then
      warn "$label not responding after ${max}s. Check logs."
      return 1
    fi
    printf "\r  ${CYAN}%-45s${RESET} %ds" "Waiting for $label…" "$elapsed"
    sleep "$interval"; elapsed=$((elapsed + interval))
  done
  printf "\r\033[2K"
  success "$label  ($url)"
}

# Infrastructure first
wait_container "collegeproject-postgres-1" 60
wait_container "collegeproject-redis-1"    30

# Backend services
wait_http "auth-service"     "http://localhost:8001/health" 90
wait_http "expense-service"  "http://localhost:8002/health" 90
wait_http "api-gateway"      "http://localhost:8000/health" 90

# Frontend (npm install + vite can be slow on first run)
wait_http "web (Vite)"       "http://localhost:3000"        180

# ── Step 9: final status table ────────────────────────────────────────────────
step "Status"
docker compose ps 2>/dev/null || true

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║         SplitEase is ready ✔             ║${RESET}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${BOLD}App          ${RESET}→  ${CYAN}http://localhost:3000${RESET}"
echo -e "  ${BOLD}API Gateway  ${RESET}→  ${CYAN}http://localhost:8000${RESET}"
echo -e "  ${BOLD}Auth API     ${RESET}→  ${CYAN}http://localhost:8001/docs${RESET}"
echo -e "  ${BOLD}Expense API  ${RESET}→  ${CYAN}http://localhost:8002/docs${RESET}"
echo ""
echo -e "  ${YELLOW}Logs     ${RESET}→  ./start.sh --logs"
echo -e "  ${YELLOW}Rebuild  ${RESET}→  ./start.sh --build"
echo -e "  ${YELLOW}Reset DB ${RESET}→  ./start.sh --fresh"
echo -e "  ${YELLOW}Stop     ${RESET}→  ./start.sh --down"
echo ""
