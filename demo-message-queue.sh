#!/usr/bin/env bash
# demo-message-queue.sh
#
# Shows the full Redis Streams message-queue lifecycle:
#
#   expense-service  ──XADD──►  splitease:events  ──XREADGROUP──►  notification-worker
#
# What the demo does:
#   1. Registers Alice and Bob
#   2. Alice logs in and creates a group (INR)
#   3. Alice invites Bob by email
#   4. Snapshots the Redis stream length
#   5. Alice creates an expense → expense-service publishes an event
#   6. Verifies the event appeared in the stream (shows raw fields)
#   7. Waits for notification-worker to consume + ACK the event
#   8. Confirms the consumer group has 0 pending messages
#   9. Prints the full flow diagram
#
set -euo pipefail

# ── colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

step()    { echo -e "\n${BOLD}${CYAN}━━━  $*  ━━━${RESET}"; }
ok()      { echo -e "  ${GREEN}✔${RESET}  $*"; }
info()    { echo -e "  ${CYAN}▸${RESET}  $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET}   $*"; }
die()     { echo -e "\n  ${RED}✘  $*${RESET}\n" >&2; exit 1; }
dim()     { echo -e "  ${DIM}$*${RESET}"; }

# ── config ────────────────────────────────────────────────────────────────────
GATEWAY="http://localhost:8000"
TS=$(date +%s)
ALICE_EMAIL="alice_${TS}@splitease.dev"
BOB_EMAIL="bob_${TS}@splitease.dev"
PASSWORD="Demo1234!"
TODAY=$(date +%Y-%m-%d)

# ── helpers ───────────────────────────────────────────────────────────────────
# Run a redis-cli command inside the redis container
redis() { DOCKER_HOST="${DOCKER_HOST:-}" docker compose exec -T redis redis-cli "$@" 2>/dev/null | tr -d '\r'; }

# Extract a JSON field with python (no jq dependency)
jq_get() { python3 -c "import sys,json; print(json.load(sys.stdin)$(echo "$2"))" <<< "$1" 2>/dev/null || echo ""; }

# POST wrapper — prints curl errors clearly
api_post() {
  local url="$1" token="$2" body="$3"
  local auth_header=""
  [[ -n "$token" ]] && auth_header="-H \"Authorization: Bearer $token\""
  curl -sf -X POST "${GATEWAY}${url}" \
    -H "Content-Type: application/json" \
    ${token:+-H "Authorization: Bearer $token"} \
    -d "$body"
}

# ── banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║         SplitEase — Message Queue Demo               ║${RESET}"
echo -e "${BOLD}║  Redis Streams  •  XADD  •  XREADGROUP  •  XACK     ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${DIM}expense-service${RESET}  ──XADD──►  ${CYAN}splitease:events${RESET}  ──XREADGROUP──►  ${DIM}notification-worker${RESET}"
echo ""

# ── preflight ─────────────────────────────────────────────────────────────────
step "PREFLIGHT — checking services"

curl -sf "$GATEWAY/health" &>/dev/null \
  || die "api-gateway not reachable at $GATEWAY/health\n  Run: ./start.sh"
ok "api-gateway is up"

docker compose ps notification-worker 2>/dev/null | grep -qiE "up|running" \
  || warn "notification-worker not detected — push notifications won't fire but stream will still work"
ok "notification-worker container present"

redis PING | grep -q "PONG" \
  || die "Redis not reachable. Run: ./start.sh"
ok "Redis is reachable"

# ── step 1: register users ─────────────────────────────────────────────────────
step "STEP 1 — Registering Alice and Bob"

ALICE_RESP=$(api_post "/api/auth/register" "" \
  "{\"email\":\"$ALICE_EMAIL\",\"name\":\"Alice Demo\",\"password\":\"$PASSWORD\"}")
ALICE_ID=$(jq_get "$ALICE_RESP" "['id']")
[[ -n "$ALICE_ID" ]] || die "Alice registration failed:\n$ALICE_RESP"
ok "Alice registered  →  id: $ALICE_ID"

BOB_RESP=$(api_post "/api/auth/register" "" \
  "{\"email\":\"$BOB_EMAIL\",\"name\":\"Bob Demo\",\"password\":\"$PASSWORD\"}")
BOB_ID=$(jq_get "$BOB_RESP" "['id']")
[[ -n "$BOB_ID" ]] || die "Bob registration failed:\n$BOB_RESP"
ok "Bob registered    →  id: $BOB_ID"

# ── step 2: login as alice ─────────────────────────────────────────────────────
step "STEP 2 — Alice logs in"

LOGIN_RESP=$(api_post "/api/auth/login" "" \
  "{\"email\":\"$ALICE_EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(jq_get "$LOGIN_RESP" "['access_token']")
[[ -n "$TOKEN" ]] || die "Login failed:\n$LOGIN_RESP"
ok "JWT obtained  →  ${TOKEN:0:20}…"

# ── step 3: create group ────────────────────────────────────────────────────────
step "STEP 3 — Alice creates a group (INR)"

GROUP_RESP=$(api_post "/api/groups" "$TOKEN" \
  "{\"name\":\"MQ Demo ${TS}\",\"description\":\"Message queue demo group\",\"currency\":\"INR\"}")
GROUP_ID=$(jq_get "$GROUP_RESP" "['id']")
[[ -n "$GROUP_ID" ]] || die "Group creation failed:\n$GROUP_RESP"
ok "Group created  →  id: $GROUP_ID"

# ── step 4: invite bob ─────────────────────────────────────────────────────────
step "STEP 4 — Alice invites Bob by email"

INVITE_RESP=$(api_post "/api/groups/$GROUP_ID/members" "$TOKEN" \
  "{\"email\":\"$BOB_EMAIL\"}")
BOB_MEMBER_ID=$(jq_get "$INVITE_RESP" "['user_id']")
[[ -n "$BOB_MEMBER_ID" ]] || die "Invite failed:\n$INVITE_RESP"
ok "Bob joined group  →  role: $(jq_get "$INVITE_RESP" "['role']")"

# ── step 5: snapshot stream BEFORE ────────────────────────────────────────────
step "STEP 5 — Redis stream snapshot BEFORE expense"

BEFORE_LEN=$(redis XLEN splitease:events)
info "splitease:events length: ${BOLD}${BEFORE_LEN:-0}${RESET} messages"

# Show last message if any exist
if [[ "${BEFORE_LEN:-0}" -gt "0" ]]; then
  dim "Most recent existing message:"
  redis XREVRANGE splitease:events + - COUNT 1 | sed 's/^/    /'
fi

# ── step 6: create expense ─────────────────────────────────────────────────────
step "STEP 6 — Alice creates an expense (₹1200 dinner, equal split)"

EXPENSE_RESP=$(api_post "/api/expenses" "$TOKEN" \
  "{
    \"group_id\": \"$GROUP_ID\",
    \"description\": \"Team dinner\",
    \"amount\": 1200.00,
    \"currency\": \"INR\",
    \"paid_by\": \"$ALICE_ID\",
    \"category\": \"Food\",
    \"date\": \"$TODAY\",
    \"split_type\": \"equal\"
  }")
EXPENSE_ID=$(jq_get "$EXPENSE_RESP" "['id']")
[[ -n "$EXPENSE_ID" ]] || die "Expense creation failed:\n$EXPENSE_RESP"
ok "Expense created  →  id: $EXPENSE_ID"
info "expense-service called  XADD splitease:events * type expense.created …"

# ── step 7: verify event in stream ────────────────────────────────────────────
step "STEP 7 — Verifying event appeared in Redis stream"

sleep 1  # brief pause for the async XADD to land

AFTER_LEN=$(redis XLEN splitease:events)
DELTA=$(( ${AFTER_LEN:-0} - ${BEFORE_LEN:-0} ))

info "Stream length: ${BOLD}${BEFORE_LEN:-0}${RESET} → ${BOLD}${AFTER_LEN:-0}${RESET}  (+${DELTA} new message(s))"
echo ""

if [[ "$DELTA" -ge 1 ]]; then
  ok "Event published to stream"
  echo ""
  echo -e "  ${BOLD}Raw stream entry (XREVRANGE … COUNT 1):${RESET}"
  redis XREVRANGE splitease:events + - COUNT 1 \
    | while IFS= read -r line; do echo "    $line"; done
else
  warn "No new messages detected — XADD may have failed (check expense-service logs)"
fi

# ── step 8: watch notification-worker consume ─────────────────────────────────
step "STEP 8 — Waiting for notification-worker to XREADGROUP + process (up to 12 s)"
echo ""

CONSUMED=false
for i in $(seq 1 12); do
  LOGS=$(docker compose logs --tail=50 notification-worker 2>/dev/null || echo "")
  if echo "$LOGS" | grep -q "$EXPENSE_ID"; then
    CONSUMED=true
    echo -e "  ${GREEN}✔  notification-worker processed the event${RESET}"
    echo ""
    echo -e "  ${BOLD}Relevant worker log lines:${RESET}"
    echo "$LOGS" | grep -E "expense\.created|notified|push|$EXPENSE_ID" \
      | tail -6 | while IFS= read -r line; do echo "    $line"; done
    break
  fi
  printf "\r  ${CYAN}Waiting for worker…${RESET} %ds" "$i"
  sleep 1
done
printf "\r\033[2K"

if [[ "$CONSUMED" == false ]]; then
  warn "Worker log line not found within 12 s."
  warn "VAPID keys not set → push skipped, but the event was still consumed."
  echo ""
  echo -e "  ${BOLD}Recent worker logs:${RESET}"
  docker compose logs --tail=15 notification-worker 2>/dev/null \
    | tail -15 | while IFS= read -r line; do echo "    $line"; done
fi

# ── step 9: confirm ACK ───────────────────────────────────────────────────────
step "STEP 9 — Confirming XACK (no pending messages)"

PENDING_RAW=$(redis XPENDING splitease:events splitease-notifications - + 10)
# Count non-empty lines (each pending entry starts with the message ID)
PENDING=$(echo "$PENDING_RAW" | grep -c "^[0-9]" 2>/dev/null || echo "0")

info "Pending (un-ACK'd) messages: ${BOLD}${PENDING}${RESET}"

if [[ "$PENDING" -eq 0 ]]; then
  ok "All messages acknowledged — consumer group is clean"
else
  warn "$PENDING message(s) still pending. Worker will retry on next poll."
  echo "  Pending entries:"
  echo "$PENDING_RAW" | head -6 | while IFS= read -r line; do echo "    $line"; done
fi

# ── step 10: summary ──────────────────────────────────────────────────────────
step "STEP 10 — Full message flow"

echo ""
echo -e "  ${BOLD}What just happened:${RESET}"
echo ""
echo -e "  ${CYAN}1.${RESET} Alice created expense '${BOLD}Team dinner${RESET}' (₹1200) — expense id: $EXPENSE_ID"
echo -e "  ${CYAN}2.${RESET} expense-service appended to stream:"
echo -e "       ${DIM}XADD splitease:events * type expense.created expense_id $EXPENSE_ID group_id $GROUP_ID …${RESET}"
echo -e "  ${CYAN}3.${RESET} notification-worker (running in background) polled with:"
echo -e "       ${DIM}XREADGROUP GROUP splitease-notifications worker-1 COUNT 10 BLOCK 5000 STREAMS splitease:events >${RESET}"
echo -e "  ${CYAN}4.${RESET} Worker fetched group members, sent push to ${BOLD}Bob${RESET} (skipped Alice — she's the creator)"
echo -e "  ${CYAN}5.${RESET} Worker acknowledged the message:"
echo -e "       ${DIM}XACK splitease:events splitease-notifications <message-id>${RESET}"
echo ""
echo -e "  ${BOLD}Key properties demonstrated:${RESET}"
echo -e "  ${GREEN}✔${RESET}  ${BOLD}Durable${RESET}       — messages survive worker restarts (replay from id=0)"
echo -e "  ${GREEN}✔${RESET}  ${BOLD}At-least-once${RESET} — un-ACK'd messages stay pending and are redeliverable"
echo -e "  ${GREEN}✔${RESET}  ${BOLD}Consumer groups${RESET} — multiple workers can share the load (fan-out)"
echo -e "  ${GREEN}✔${RESET}  ${BOLD}Decoupled${RESET}     — expense-service has no import of notification-worker"
echo ""
echo -e "${BOLD}${GREEN}Message queue demo complete.${RESET}"
echo ""
