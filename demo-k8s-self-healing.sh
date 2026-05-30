#!/usr/bin/env bash
# demo-k8s-self-healing.sh
# Demonstrates Kubernetes self-healing: delete a pod, watch it automatically restart.
#
# Prerequisites: minikube running with SplitEase deployed.
#   If not deployed yet, run:  bash scripts/demo-k8s.sh  (steps 1-3 only)
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

step()    { echo -e "\n${BOLD}${CYAN}━━━ $* ━━━${RESET}"; }
info()    { echo -e "  ${CYAN}$*${RESET}"; }
success() { echo -e "  ${GREEN}✔  $*${RESET}"; }
warn()    { echo -e "  ${YELLOW}⚠  $*${RESET}"; }

NS="splitease"
TARGET_DEPLOY="api-gateway"  # pod to kill for the demo

echo -e "\n${BOLD}╔══════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   SplitEase — Kubernetes Self-Healing Demo   ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${RESET}"

# ─── Preflight ────────────────────────────────────────────────────────────────
step "PREFLIGHT — Checking cluster"
if ! kubectl cluster-info &>/dev/null; then
  echo -e "${RED}[ERROR]${RESET} kubectl cannot reach a cluster."
  echo "        Start minikube:  minikube start"
  echo "        Then deploy:     bash scripts/demo-k8s.sh"
  exit 1
fi
success "Cluster reachable."

if ! kubectl get ns "$NS" &>/dev/null; then
  echo -e "${RED}[ERROR]${RESET} Namespace '$NS' not found — deploy the app first:"
  echo "        bash scripts/demo-k8s.sh"
  exit 1
fi
success "Namespace '$NS' found."

# ─── Step 1: Show healthy cluster state ───────────────────────────────────────
step "STEP 1 — Current pod state (all healthy)"
kubectl get pods -n "$NS" -o wide
echo ""
info "Every pod has STATUS=Running and RESTARTS=0."

# ─── Step 2: Show the target pod is actually serving traffic ──────────────────
step "STEP 2 — Confirming $TARGET_DEPLOY is serving requests"
POD=$(kubectl get pod -n "$NS" -l "app=$TARGET_DEPLOY" -o jsonpath='{.items[0].metadata.name}')
info "Pod: $POD"
kubectl exec -n "$NS" "$POD" -- \
  python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
success "$TARGET_DEPLOY health check passed."

# ─── Step 3: Kill the pod ────────────────────────────────────────────────────
step "STEP 3 — Forcefully deleting pod '$POD'"
info "Kubernetes ReplicaSet will immediately schedule a replacement."
kubectl delete pod "$POD" -n "$NS" --grace-period=0 --force 2>/dev/null || \
kubectl delete pod "$POD" -n "$NS"
success "Pod deleted."

# ─── Step 4: Watch Kubernetes recreate it ─────────────────────────────────────
step "STEP 4 — Watching Kubernetes self-heal (up to 60 s)"
echo ""
SECONDS_WAITED=0
while true; do
  STATUS=$(kubectl get pods -n "$NS" -l "app=$TARGET_DEPLOY" \
    --no-headers 2>/dev/null | awk '{print $3}' | head -1)
  NAME=$(kubectl get pods -n "$NS" -l "app=$TARGET_DEPLOY" \
    --no-headers 2>/dev/null | awk '{print $1}' | head -1)
  echo -ne "  ${CYAN}${SECONDS_WAITED}s${RESET}  pod: ${BOLD}$NAME${RESET}  status: "
  case "$STATUS" in
    Running)  echo -e "${GREEN}$STATUS${RESET}" ;;
    Pending)  echo -e "${YELLOW}$STATUS${RESET}" ;;
    *)        echo -e "${RED}$STATUS${RESET}" ;;
  esac

  if [ "$STATUS" = "Running" ] && [ "$NAME" != "$POD" ]; then
    echo ""
    success "New pod '$NAME' is Running — self-healing confirmed."
    break
  fi
  if [ "$SECONDS_WAITED" -ge 60 ]; then
    warn "Timed out after 60 s. Check: kubectl describe pod -n $NS -l app=$TARGET_DEPLOY"
    break
  fi
  sleep 3
  SECONDS_WAITED=$((SECONDS_WAITED + 3))
done

# ─── Step 5: Final state ──────────────────────────────────────────────────────
step "STEP 5 — Final cluster state"
kubectl get pods -n "$NS" -o wide
echo ""
info "RESTARTS counter on the old pod was 0. A brand-new pod replaced it."
info "Zero manual intervention was needed."

# ─── Step 6: Verify new pod serves traffic ────────────────────────────────────
step "STEP 6 — Confirming new pod serves traffic"
NEW_POD=$(kubectl get pod -n "$NS" -l "app=$TARGET_DEPLOY" -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n "$NS" "$NEW_POD" -- \
  python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
success "New pod '$NEW_POD' is healthy and serving requests."

echo -e "\n${BOLD}${GREEN}Self-healing demo complete.${RESET}"
echo -e "  Kubernetes detected the missing pod and scheduled a replacement automatically."
echo -e "  Downtime was limited to the pod startup time (~seconds).\n"
