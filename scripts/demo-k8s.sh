#!/usr/bin/env bash
# =============================================================================
# SplitEase — Kubernetes Demo Script
# Demonstrates: cluster startup, service deployment, scale-up, scale-down, HPA
#
# Prerequisites:
#   brew install minikube kubectl
#   minikube start (or let this script do it)
# =============================================================================
set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

K8S_DIR="$(cd "$(dirname "$0")/../k8s" && pwd)"
NS="splitease"

banner()  { echo -e "\n${BOLD}${CYAN}══════════════════════════════════════════${RESET}"; echo -e "${BOLD}${CYAN}  $1${RESET}"; echo -e "${BOLD}${CYAN}══════════════════════════════════════════${RESET}\n"; }
step()    { echo -e "${BOLD}${GREEN}▶ $1${RESET}"; }
info()    { echo -e "  ${CYAN}$1${RESET}"; }
warn()    { echo -e "  ${YELLOW}⚠  $1${RESET}"; }
success() { echo -e "  ${GREEN}✔  $1${RESET}"; }
pause()   { echo -e "\n${YELLOW}[Press ENTER to continue...]${RESET}"; read -r; }

# ── STEP 1: Start Minikube ────────────────────────────────────────────────────
banner "STEP 1 — Start Minikube Cluster"

if minikube status --profile minikube 2>/dev/null | grep -q "Running"; then
    success "Minikube is already running"
else
    step "Starting Minikube with 4 CPUs and 4 GB RAM..."
    minikube start --cpus=4 --memory=4096 --driver=docker
    success "Minikube started"
fi

step "Enabling required addons..."
minikube addons enable metrics-server
minikube addons enable ingress
success "Addons enabled: metrics-server, ingress"

step "Cluster info:"
kubectl cluster-info
echo ""
kubectl get nodes -o wide

pause

# ── STEP 2: Build Images Inside Minikube ─────────────────────────────────────
banner "STEP 2 — Build Docker Images (inside Minikube)"

step "Pointing Docker to Minikube's daemon..."
eval "$(minikube docker-env)"
success "Docker now targeting Minikube"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

step "Building api-gateway..."
docker build -t splitease/api-gateway:latest "$ROOT/services/api-gateway"

step "Building auth-service..."
docker build -t splitease/auth-service:latest "$ROOT/services/auth-service"

step "Building expense-service..."
docker build -t splitease/expense-service:latest "$ROOT/services/expense-service"

step "Building notification-worker..."
docker build -t splitease/notification-worker:latest "$ROOT/services/notification-worker"

step "Building web (React + nginx)..."
docker build -t splitease/web:latest "$ROOT/apps/web"

success "All images built"
docker images | grep splitease

pause

# ── STEP 3: Deploy All Services ───────────────────────────────────────────────
banner "STEP 3 — Deploy All Services to Kubernetes"

step "Applying manifests..."
kubectl apply -f "$K8S_DIR/00-namespace.yaml"
kubectl apply -f "$K8S_DIR/01-configmap.yaml"
kubectl apply -f "$K8S_DIR/02-secrets.yaml"

kubectl apply -f "$K8S_DIR/postgres/"
kubectl apply -f "$K8S_DIR/redis/"

step "Waiting for postgres and redis..."
kubectl rollout status statefulset/postgres -n $NS --timeout=90s
kubectl rollout status deployment/redis      -n $NS --timeout=60s
success "Databases ready"

kubectl apply -f "$K8S_DIR/auth-service/"
kubectl apply -f "$K8S_DIR/expense-service/"
kubectl apply -f "$K8S_DIR/api-gateway/"
kubectl apply -f "$K8S_DIR/notification-worker/"
kubectl apply -f "$K8S_DIR/web/"
kubectl apply -f "$K8S_DIR/ingress.yaml"

step "Waiting for all application deployments..."
kubectl rollout status deployment/auth-service        -n $NS --timeout=120s
kubectl rollout status deployment/expense-service     -n $NS --timeout=120s
kubectl rollout status deployment/api-gateway         -n $NS --timeout=120s
kubectl rollout status deployment/notification-worker -n $NS --timeout=120s
kubectl rollout status deployment/web                 -n $NS --timeout=120s

success "All services deployed!"
echo ""
echo -e "${BOLD}All running Pods:${RESET}"
kubectl get pods -n $NS -o wide

echo ""
echo -e "${BOLD}All Services:${RESET}"
kubectl get services -n $NS

pause

# ── STEP 4: Show Running Cluster State ───────────────────────────────────────
banner "STEP 4 — Current Cluster State"

echo -e "${BOLD}Deployments:${RESET}"
kubectl get deployments -n $NS

echo ""
echo -e "${BOLD}HorizontalPodAutoscalers:${RESET}"
kubectl get hpa -n $NS

echo ""
echo -e "${BOLD}App URL:${RESET}"
APP_URL=$(minikube service web -n $NS --url 2>/dev/null || echo "run: minikube tunnel, then visit http://splitease.local")
info "$APP_URL"

pause

# ── STEP 5: Manual Scale UP ───────────────────────────────────────────────────
banner "STEP 5 — Scale UP (manual)"

step "Scaling api-gateway from 1 → 3 replicas..."
kubectl scale deployment/api-gateway -n $NS --replicas=3

step "Scaling auth-service from 1 → 2 replicas..."
kubectl scale deployment/auth-service -n $NS --replicas=2

step "Scaling expense-service from 1 → 2 replicas..."
kubectl scale deployment/expense-service -n $NS --replicas=2

step "Waiting for rollout..."
kubectl rollout status deployment/api-gateway     -n $NS --timeout=60s
kubectl rollout status deployment/auth-service    -n $NS --timeout=60s
kubectl rollout status deployment/expense-service -n $NS --timeout=60s

success "Scale UP complete"
echo ""
kubectl get pods -n $NS -o wide

pause

# ── STEP 6: Manual Scale DOWN ─────────────────────────────────────────────────
banner "STEP 6 — Scale DOWN (manual)"

step "Scaling api-gateway back to 1 replica..."
kubectl scale deployment/api-gateway -n $NS --replicas=1

step "Scaling auth-service back to 1 replica..."
kubectl scale deployment/auth-service -n $NS --replicas=1

step "Scaling expense-service back to 1 replica..."
kubectl scale deployment/expense-service -n $NS --replicas=1

sleep 5
success "Scale DOWN complete"
echo ""
kubectl get pods -n $NS -o wide

pause

# ── STEP 7: Horizontal Pod Autoscaler Demo ────────────────────────────────────
banner "STEP 7 — Horizontal Pod Autoscaler (HPA)"

echo -e "${BOLD}Current HPA status:${RESET}"
kubectl get hpa -n $NS

echo ""
step "Generating CPU load on api-gateway to trigger auto-scaling..."
info "Running a load-generator pod for 60 seconds..."

# Fire a load generator in the background and watch HPA for 90 s
kubectl run load-gen \
    --image=busybox:1.36 \
    --restart=Never \
    -n $NS \
    -- sh -c "while true; do wget -q -O- http://api-gateway:8000/health; done" &
LOAD_PID=$!

echo ""
info "Watching HPA (refreshes every 10 s for 90 s)..."
for i in $(seq 1 9); do
    sleep 10
    echo -e "\n${CYAN}── tick $i / 9 ──${RESET}"
    kubectl get hpa -n $NS
    kubectl get pods -n $NS --no-headers | grep -E "api-gateway|auth-service|expense"
done

step "Stopping load generator..."
kubectl delete pod load-gen -n $NS --ignore-not-found=true 2>/dev/null || true
wait $LOAD_PID 2>/dev/null || true

success "HPA demo complete"
echo ""
echo -e "${BOLD}Final HPA status:${RESET}"
kubectl get hpa -n $NS

pause

# ── STEP 8: Cleanup Prompt ───────────────────────────────────────────────────
banner "STEP 8 — Optional Cleanup"

echo -e "  Delete all SplitEase resources?  ${YELLOW}(y/N)${RESET}"
read -r CLEANUP
if [[ "$CLEANUP" =~ ^[Yy]$ ]]; then
    kubectl delete namespace $NS
    success "Namespace '$NS' deleted — all resources removed"
else
    warn "Resources kept. To clean up later: kubectl delete namespace $NS"
    warn "To stop Minikube: minikube stop"
fi

echo ""
banner "Demo Complete!"
success "SplitEase Kubernetes demo finished successfully."
echo ""
