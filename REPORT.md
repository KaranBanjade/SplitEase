# SplitEase — Project Report

**Course Project | Microservices Architecture**

---

## Table of Contents

1. [Domain Description](#1-domain-description)
2. [The Four Services](#2-the-four-services)
3. [System Architecture Diagram](#3-system-architecture-diagram)
4. [Communication Flows](#4-communication-flows)
5. [Architectural Decisions](#5-architectural-decisions)
6. [Source Code & Deployment Artifacts](#6-source-code--deployment-artifacts)

---

## 1. Domain Description

**SplitEase** is a shared-expense tracking application in the style of Splitwise. It solves a common real-world problem: when a group of people (flatmates, travel companions, friends) share costs, tracking who paid what and who owes whom becomes complex quickly.

### Core Domain Concepts

| Concept | Description |
|---|---|
| **Group** | A collection of users sharing expenses (e.g. "Goa Trip", "Flat 4B") |
| **Expense** | A payment made by one member on behalf of the group, split among participants |
| **Split** | Each member's share of an expense — equal, exact amount, or percentage |
| **Balance** | A user's net position within a group (positive = owed money, negative = owes money) |
| **Settlement** | A direct payment from one member to another that clears part of their debt |
| **Simplified Debt** | The minimum set of payments that would settle all balances in a group |

### Split Modes

The application supports three ways to divide an expense:

- **Equal** — amount divided evenly among all group members
- **Exact** — each member is assigned a specific amount (must sum to total)
- **Percentage** — each member is assigned a percentage share (must sum to 100%)

### Users & Notifications

Users register with email and password. When a new expense is added to a group, every other member receives a real-time browser push notification. Weekly email digests summarise outstanding balances. Recurring expenses (daily / weekly / monthly / yearly) are created automatically by a background scheduler.

---

## 2. The Four Services

### Service 1 — API Gateway (Port 8000)

**Role:** Single entry point for all client traffic. It is the only service exposed to the internet.

**Responsibilities:**

- **JWT Authentication** — validates Bearer tokens on every protected route locally (shared secret key), without making a round-trip to the auth service. Attaches the extracted `user_id` as an `X-User-Id` header on forwarded requests.
- **Rate Limiting** — sliding-window counter per IP address, stored in Redis sorted sets. Limit: 100 requests per minute. Falls back to an in-process dictionary if Redis is unavailable.
- **Request Proxying** — forwards requests to the correct downstream service by path prefix, stripping the `/api` prefix before forwarding.
- **Circuit Breaker** — custom async implementation (`proxy.py`). Opens after 3 consecutive connection failures to a downstream service. In the open state, requests are rejected immediately (HTTP 503) rather than queuing up. After 30 seconds, one probe request is allowed through (half-open); on success the breaker closes.
- **Aggregate Endpoint** — `GET /api/dashboard` fires three upstream requests concurrently (user profile, group list, per-group balances) and merges them into one response, reducing frontend round-trips.

**Route Table:**

| Path Prefix | Forwarded To |
|---|---|
| `/api/auth/*` | Auth Service :8001 |
| `/api/groups/*` | Expense Service :8002 |
| `/api/expenses/*` | Expense Service :8002 |
| `/api/settlements/*` | Expense Service :8002 |
| `/api/recurring/*` | Expense Service :8002 |

**Key files:** `main.py`, `proxy.py`, `middleware/auth.py`, `middleware/rate_limit.py`, `routers/aggregate.py`

---

### Service 2 — Auth Service (Port 8001)

**Role:** Owns all user identity and session data. No other service writes to `auth_schema`.

**Responsibilities:**

- **Registration** — validates email uniqueness, hashes password with bcrypt (`passlib`), issues a JWT access token (15 min TTL) and a UUID-based refresh token stored in the database (7-day TTL).
- **Login** — verifies bcrypt hash, prunes expired refresh tokens, issues new token pair.
- **Token Refresh** — exchanges a valid refresh token for a new access token. The refresh token is looked up by SHA-256 hash (never stored in plain text).
- **Logout** — deletes the refresh token from the database. Logout is real — tokens cannot be replayed after this.
- **Password Reset** — generates a time-limited reset token, sends it via email (SMTP), validates and applies the new password.
- **Web Push Subscriptions** — stores browser push subscription objects (`endpoint`, `p256dh`, `auth_key`) for VAPID-signed Web Push notifications.
- **Internal User Lookup** — `GET /internal/users?ids=[...]` — batch endpoint consumed by the expense service to enrich expense data with user names and avatars without exposing those fields in the main auth API.

**Database:** `auth_schema` — tables: `users`, `refresh_tokens`, `password_resets`, `push_subscriptions`

**Key files:** `routers/auth.py`, `routers/users.py`, `utils/jwt.py`, `utils/password.py`, `utils/email.py`

---

### Service 3 — Expense Service (Port 8002)

**Role:** Owns all financial data. The most complex service.

**Responsibilities:**

- **Group Management** — CRUD for groups. Owners can invite members by email (looked up via auth service) and remove members. Groups have a base currency.
- **Expense Management** — CRUD for expenses. On creation, calls `_calculate_splits()` to produce per-member `share_amount` and `owed_amount` rows. On update, recalculates splits if amount or split type changed.
- **Debt Simplification** — `GET /groups/{id}/simplified-debts` runs the greedy algorithm described below. Returns the minimum list of `(debtor → creditor, amount)` transactions that would fully settle the group.
- **Settlement Recording** — `POST /settlements` records a payment, then walks through unsettled splits in chronological order, marking them settled or reducing their `owed_amount` for partial payments.
- **Recurring Expenses** — CRUD for recurring expense templates. The notification worker creates real expense instances from these on schedule.
- **Redis Stream Publishing** — after each expense creation, publishes an `expense.created` event to the `splitease:events` Redis Stream, enabling asynchronous notification without coupling to the notification worker.

**Split Calculation Logic (`routers/expenses.py`):**

```
Equal:      base = floor(total / n)
            remainder = total - (base × n)
            person[0] receives base + remainder (penny adjustment)

Exact:      validates sum(amounts) ≈ total (±0.02 tolerance)

Percentage: validates sum(pct) = 100 (±0.01 tolerance)
            share = floor(pct/100 × total)
            person[0] absorbs rounding remainder
```

**Debt Simplification Algorithm (`utils/debt_simplification.py`):**

```
1. Calculate net balance for each user:
   - payer gets +owed_amount for each split they funded
   - debtor gets -owed_amount for each split they owe
   - settlements offset both sides

2. Partition into creditors (balance > 0) and debtors (balance < 0)
3. Sort both lists descending by absolute value
4. Greedy match: largest debtor pays largest creditor
   settle = min(debt, credit)
   Advance pointer when one side reaches zero

Result: O(N log N) time, produces the minimum number of transactions
```

Example: 4 people, 6 expenses → up to 12 raw debts → reduced to 3 payments.

**Database:** `expenses_schema` — tables: `groups`, `group_members`, `expenses`, `expense_splits`, `settlements`, `recurring_expenses`

**Key files:** `routers/expenses.py`, `routers/groups.py`, `routers/settlements.py`, `routers/recurring.py`, `utils/debt_simplification.py`

---

### Service 4 — Notification Worker (Headless)

**Role:** Asynchronous background worker. No HTTP server. Runs two concurrent async components.

**Component A — Redis Stream Consumer (`workers/event_consumer.py`):**

Listens on stream `splitease:events` using a consumer group (`splitease-notifications`). On each `expense.created` event:
1. Fetches all group member IDs from the database
2. Skips the expense creator
3. Sends a VAPID-signed Web Push notification to every other member's registered devices
4. Acknowledges the message with `XACK`

The consumer uses `XREADGROUP ... BLOCK 5000` — it blocks for 5 seconds waiting for new messages, then loops. This means the event loop yields regularly and `CancelledError` propagates cleanly on shutdown.

**Component B — APScheduler Jobs:**

| Job | Schedule | What it does |
|---|---|---|
| `process_recurring_expenses` | Daily 09:00 UTC | Finds recurring expense templates past their `next_due` date, creates real expense rows, advances `next_due` |
| `send_weekly_digests` | Monday 08:00 UTC | Emails each user their outstanding balance summary across all groups |
| `send_settlement_reminders` | Monday 09:00 UTC | Sends push notifications to users with unsettled debts older than 7 days |

**Graceful Shutdown:** catches `SIGINT`/`SIGTERM`, cancels the consumer task, waits for it to finish, then shuts down the scheduler.

**Key files:** `main.py`, `workers/event_consumer.py`, `workers/push_worker.py`, `workers/email_worker.py`, `workers/recurring_worker.py`

---

## 3. System Architecture Diagram

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                   │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐     │
│   │  Browser / PWA (React 18 + TypeScript + Vite)                    │     │
│   │  • TanStack Query (server state, caching)                        │     │
│   │  • Zustand (auth token, offline queue)                           │     │
│   │  • Workbox Service Worker (offline cache, background sync)       │     │
│   └──────────┬─────────────────────────────────────┬────────────────┘     │
│              │ HTTPS /api/*                         │ HTTPS static         │
└──────────────┼─────────────────────────────────────┼──────────────────────┘
               │                                     │
               ▼                                     ▼
┌──────────────────────────┐          ┌──────────────────────────┐
│   API GATEWAY  :8000     │          │   S3 + CloudFront        │
│                          │          │   (static frontend)      │
│  ┌────────────────────┐  │          └──────────────────────────┘
│  │  Rate Limit MW     │  │
│  │  (Redis sorted set)│  │
│  └────────────────────┘  │
│  ┌────────────────────┐  │
│  │  Auth MW           │  │
│  │  (JWT decode local)│  │
│  └────────────────────┘  │
│  ┌────────────────────┐  │
│  │  Circuit Breaker   │  │
│  │  (per upstream)    │  │
│  └────────────────────┘  │
│  ┌────────────────────┐  │
│  │  Proxy / Router    │  │
│  └──────┬─────────────┘  │
└─────────┼────────────────┘
          │
     ┌────┴─────────────────────┐
     │                          │
     ▼                          ▼
┌────────────────────┐   ┌────────────────────────────────────────────┐
│  AUTH SERVICE      │   │  EXPENSE SERVICE  :8002                    │
│  :8001             │   │                                            │
│                    │◄──│  GET /internal/users?ids=[...]             │
│  • Register/Login  │   │                                            │
│  • JWT issuance    │   │  • Groups (CRUD)                           │
│  • Token refresh   │   │  • Expenses (CRUD + split calc)            │
│  • Password reset  │   │  • Settlements (record + apply)            │
│  • Push sub mgmt   │   │  • Balances + Debt Simplification          │
│  • Internal user   │   │  • Recurring expense templates             │
│    lookup API      │   │  • Publishes to Redis Stream ──────────┐   │
└────────┬───────────┘   └─────────────────┬──────────────────────┼───┘
         │                                 │                      │
         ▼                                 ▼                      │
┌────────────────────────────────────────────────────────┐       │
│   PostgreSQL  (single instance, two schemas)           │       │
│                                                        │       │
│   auth_schema:                expenses_schema:         │       │
│   • users                     • groups                 │       │
│   • refresh_tokens            • group_members          │       │
│   • password_resets           • expenses               │       │
│   • push_subscriptions        • expense_splits         │       │
│                               • settlements            │       │
│                               • recurring_expenses     │       │
└────────────────────────────────────────────────────────┘       │
                                                                  │
         ┌────────────────────────────────────────────────────────┘
         ▼
┌────────────────────────────────────────────────────────┐
│   Redis  (single instance, two responsibilities)       │
│                                                        │
│   • Rate-limit counters   (sorted sets, key per IP)    │
│   • Refresh token store   (auth service)               │
│   • splitease:events      (Redis Stream)               │
└──────────────────────────────┬─────────────────────────┘
                               │ XREADGROUP
                               ▼
┌────────────────────────────────────────────────────────┐
│   NOTIFICATION WORKER  (headless async process)        │
│                                                        │
│   ┌───────────────────────┐  ┌──────────────────────┐  │
│   │  Redis Stream         │  │  APScheduler         │  │
│   │  Consumer             │  │  • Daily: recurring  │  │
│   │  (XREADGROUP + XACK)  │  │  • Weekly: digest    │  │
│   │  → push on expense    │  │  • Weekly: reminders │  │
│   │    created            │  └──────────────────────┘  │
│   └───────────────────────┘                            │
│                │                                       │
│                ▼                                       │
│   ┌─────────────────────────────┐                      │
│   │  Dispatch                   │                      │
│   │  • Web Push (pywebpush)     │──► Browser           │
│   │  • Email (aiosmtplib/SMTP)  │──► Inbox             │
│   └─────────────────────────────┘                      │
└────────────────────────────────────────────────────────┘
```

### Infrastructure Diagram (Production — AWS)

```
Internet
   │
   ├──► CloudFront ──► S3  (React SPA, static assets)
   │
   └──► ALB (Application Load Balancer)
              │
              └──► ECS Fargate (Private VPC Subnet)
                       ├── api-gateway   (256 CPU / 512 MB)
                       ├── auth-service  (256 CPU / 512 MB)
                       ├── expense-svc   (256 CPU / 512 MB)
                       └── notif-worker  (128 CPU / 256 MB)
                                │
                     ┌──────────┴───────────┐
                     ▼                      ▼
              RDS PostgreSQL 16      ElastiCache Redis 7
              (db.t4g.micro)         (cache.t3.micro)
                     │
              SSM Parameter Store  (secrets)
              ECR                  (Docker images)
              CloudWatch Logs      (log aggregation)
```

---

## 4. Communication Flows

### 4.1 User Registration & Login

```
Client          API Gateway         Auth Service        PostgreSQL      Redis
  │                  │                   │                   │            │
  │  POST /register  │                   │                   │            │
  │─────────────────►│                   │                   │            │
  │                  │  (public route –  │                   │            │
  │                  │   no JWT check)   │                   │            │
  │                  │  POST /auth/register                  │            │
  │                  │──────────────────►│                   │            │
  │                  │                   │  SELECT users     │            │
  │                  │                   │  WHERE email=?    │            │
  │                  │                   │──────────────────►│            │
  │                  │                   │  (no match)       │            │
  │                  │                   │◄──────────────────│            │
  │                  │                   │  INSERT user      │            │
  │                  │                   │  INSERT refresh_  │            │
  │                  │                   │  token            │            │
  │                  │                   │──────────────────►│            │
  │                  │                   │  {access_token,   │            │
  │                  │                   │   refresh_token,  │            │
  │                  │                   │   user}           │            │
  │                  │◄──────────────────│                   │            │
  │  201 Created     │                   │                   │            │
  │◄─────────────────│                   │                   │            │
```

### 4.2 Create Expense (Happy Path)

```
Client      API Gateway     Expense Service     Auth Service    PostgreSQL    Redis Stream
  │              │                │                  │               │              │
  │ POST         │                │                  │               │              │
  │ /api/        │                │                  │               │              │
  │ expenses     │                │                  │               │              │
  │─────────────►│                │                  │               │              │
  │              │ JWT decode     │                  │               │              │
  │              │ (local,        │                  │               │              │
  │              │  no HTTP call) │                  │               │              │
  │              │ POST /expenses │                  │               │              │
  │              │ + X-User-Id    │                  │               │              │
  │              │───────────────►│                  │               │              │
  │              │                │ SELECT           │               │              │
  │              │                │ group_members    │               │              │
  │              │                │──────────────────────────────────►              │
  │              │                │ GET /internal/   │               │              │
  │              │                │ users?ids=[...]  │               │              │
  │              │                │─────────────────►│               │              │
  │              │                │ [{id,name,email}]│               │              │
  │              │                │◄─────────────────│               │              │
  │              │                │ _calculate_splits│               │              │
  │              │                │ (in-process)     │               │              │
  │              │                │ INSERT expense + │               │              │
  │              │                │ expense_splits   │               │              │
  │              │                │──────────────────────────────────►              │
  │              │                │ XADD             │               │              │
  │              │                │ splitease:events │               │              │
  │              │                │──────────────────────────────────────────────────►
  │              │                │ 201 {expense}    │               │              │
  │              │◄───────────────│                  │               │              │
  │ 201 Created  │                │                  │               │              │
  │◄─────────────│                │                  │               │              │
```

*Asynchronously, within seconds:*

```
Notification Worker         Redis Stream        PostgreSQL        Browser
        │                        │                   │               │
        │  XREADGROUP            │                   │               │
        │  (block 5000ms)        │                   │               │
        │───────────────────────►│                   │               │
        │  [(msg_id, fields)]    │                   │               │
        │◄───────────────────────│                   │               │
        │  SELECT group_members  │                   │               │
        │───────────────────────────────────────────►│               │
        │  [member_ids]          │                   │               │
        │◄───────────────────────────────────────────│               │
        │  Web Push (VAPID)      │                   │               │
        │────────────────────────────────────────────────────────────►
        │  XACK splitease:events │                   │               │
        │───────────────────────►│                   │               │
```

### 4.3 Settle Debt

```
Client      API Gateway     Expense Service         PostgreSQL
  │              │                │                      │
  │ POST         │                │                      │
  │ /api/        │                │                      │
  │ settlements  │                │                      │
  │─────────────►│                │                      │
  │              │ POST /settlements                      │
  │              │───────────────►│                      │
  │              │                │ Verify membership    │
  │              │                │─────────────────────►│
  │              │                │ INSERT settlement    │
  │              │                │─────────────────────►│
  │              │                │ SELECT unsettled     │
  │              │                │ splits WHERE         │
  │              │                │   paid_by=creditor   │
  │              │                │   user_id=debtor     │
  │              │                │   currency=match     │
  │              │                │   order by date asc  │
  │              │                │─────────────────────►│
  │              │                │ Walk splits:         │
  │              │                │   split ≤ remaining  │
  │              │                │     → mark settled   │
  │              │                │   split > remaining  │
  │              │                │     → reduce owed_   │
  │              │                │       amount         │
  │              │                │ UPDATE splits        │
  │              │                │─────────────────────►│
  │              │◄───────────────│ 201 {settlement}     │
  │◄─────────────│                │                      │
```

---

## 5. Architectural Decisions

### Decision 1 — Synchronous REST with a Circuit Breaker Pattern

**Context:** The API Gateway must proxy requests to two downstream services. In a microservices deployment, any downstream service can become slow or unresponsive, and a naive proxy will block waiting for timeouts.

**Decision:** Use **synchronous HTTP (REST)** for all request/response communication between gateway and services, augmented with a **Circuit Breaker** per upstream service.

**Implementation:** A custom `AsyncCircuitBreaker` class in `proxy.py` wraps every `httpx` call. The breaker has three states:

| State | Behaviour | Transition |
|---|---|---|
| **Closed** | Requests flow normally | → Open after 3 consecutive `ConnectError` or `TimeoutException` |
| **Open** | Requests rejected immediately (HTTP 503) | → Half-Open after 30 s |
| **Half-Open** | One probe request allowed through | → Closed on success; → Open on failure |

**Why:** Synchronous REST is the appropriate style here because the gateway must return a response to the client synchronously. The circuit breaker prevents a failing downstream (e.g. auth-service restart) from exhausting the gateway's connection pool with slow timeouts. Fast-failing returns HTTP 503 in microseconds rather than waiting 30 seconds per request.

**Alternatives considered:**
- *No circuit breaker* — gateway would queue hundreds of requests during a downstream restart, each holding a connection open for the full 30-second timeout.
- *Async messaging for all calls* — inappropriate for request/response semantics where the client needs an immediate answer.

---

### Decision 2 — Asynchronous Event-Driven Notifications via Redis Streams

**Context:** When an expense is created, group members should be notified. The notification logic (fetching member data, signing VAPID tokens, calling the browser push API) is slow and not part of the atomic transaction. Doing it synchronously inside the expense creation handler would increase latency for the user.

**Decision:** Use **Redis Streams** as a message queue between expense-service (producer) and notification-worker (consumer), implementing an **event-driven asynchronous** communication pattern.

**How it works:**

1. Expense-service calls `XADD splitease:events * type expense.created expense_id <id> ...` immediately after committing the expense.
2. Notification-worker runs `XREADGROUP GROUP splitease-notifications worker-1 ... BLOCK 5000 STREAMS splitease:events >` in a continuous loop.
3. On receiving the event, the worker sends push notifications to group members.
4. After dispatching, the worker calls `XACK` to acknowledge the message.

**Why Redis Streams over alternatives:**

| Option | Why not chosen |
|---|---|
| Redis Pub/Sub | Not durable — if the worker is restarted, messages published during downtime are lost |
| RabbitMQ / Kafka | Additional infrastructure to deploy and manage; overkill for the notification volume |
| Database polling | Simpler but adds load to PostgreSQL; less real-time than streams |
| Direct HTTP call from expense-service | Creates tight coupling; blocks expense creation on notification success |

Redis Streams give **at-least-once delivery** (un-ACK'd messages are redeliverable), **consumer groups** (multiple workers could share the load), and **durability** (messages survive worker restarts). Redis is already in the stack for rate limiting, so no new infrastructure is added.

---

### Decision 3 — Single PostgreSQL Instance with Separate Schemas

**Context:** Three of the four services need persistent storage. A canonical microservices approach gives each service its own database, enforcing strict data isolation.

**Decision:** Use a **single PostgreSQL instance** with **two schemas** (`auth_schema`, `expenses_schema`) rather than two separate database servers.

**Enforcement:** Application code (SQLAlchemy models) targets a specific schema via `__table_args__ = {"schema": "auth_schema"}`. No service's ORM models reference the other service's schema. Cross-service data access happens exclusively through internal HTTP calls (e.g. expense-service calls `GET /internal/users?ids=[...]` on auth-service — never directly querying `auth_schema.users`).

**Why:**

| Concern | Single instance + schemas | Separate instances |
|---|---|---|
| **Cost** | One RDS db.t4g.micro ~₹1,000/mo | Three instances ~₹3,000/mo |
| **Operational complexity** | One backup, one connection pool, one migration pipeline | Three of each |
| **Data isolation** | Logical (schema boundary + code convention) | Physical (network boundary) |
| **Migration path** | `pg_dump --schema=expenses_schema` → new instance | Already separated |
| **Local development** | One container | Three containers |

For this project's scale (<10,000 users, college demo), the logical isolation is sufficient. The schema boundary makes the migration to physical isolation straightforward if the system ever needed to scale independently.

---

### Decision 4 — API Gateway Performs JWT Validation Locally

**Context:** Every authenticated request must be authorised. One approach is to forward the JWT to the auth-service for validation on each request. Another is to validate locally.

**Decision:** The API Gateway **decodes and validates JWTs itself** using the shared `SECRET_KEY`, rather than calling the auth-service on every request.

**Why:** JWT validation is a pure cryptographic operation — it requires only the token and the secret key. There is no state to look up (unlike opaque tokens). Making an HTTP call to auth-service on every request would:
- Add ~5–20 ms latency to every API call
- Make every request dependent on auth-service availability
- Double the load on auth-service

The gateway attaches the validated `user_id` as an `X-User-Id` header, which downstream services trust without re-validating. This is safe because downstream services are only reachable from inside the private VPC subnet — they are not internet-facing.

**Trade-off:** JWTs cannot be individually revoked before expiry (15 minutes). Logout only invalidates the refresh token. A user whose access token was stolen retains access for up to 15 minutes. This is the standard JWT trade-off, accepted here because the 15-minute window is short and the alternative (opaque tokens with server-side lookup) adds latency to every request.

---

## 6. Source Code & Deployment Artifacts

### Service Source Code

| Service | Directory | Entry Point | Framework |
|---|---|---|---|
| API Gateway | `services/api-gateway/` | `main.py` | FastAPI |
| Auth Service | `services/auth-service/` | `main.py` | FastAPI |
| Expense Service | `services/expense-service/` | `main.py` | FastAPI |
| Notification Worker | `services/notification-worker/` | `main.py` | asyncio + APScheduler |
| Frontend | `apps/web/` | `src/main.tsx` | React + Vite |

### Dockerfiles

Each service has its own `Dockerfile` following the same pattern:

```
services/api-gateway/Dockerfile
services/auth-service/Dockerfile
services/expense-service/Dockerfile
services/notification-worker/Dockerfile
apps/web/Dockerfile
```

Common pattern (Python services):
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libpq-dev gcc
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Docker Compose (Local Development)

**File:** `docker-compose.yml`

Defines 7 services:

| Service | Image | Ports | Dependencies |
|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | — |
| `redis` | redis:7-alpine | 6379 | — |
| `auth-service` | ./services/auth-service | 8001 | postgres, redis |
| `expense-service` | ./services/expense-service | 8002 | postgres, redis, auth-service |
| `api-gateway` | ./services/api-gateway | 8000 | redis, auth-service, expense-service |
| `notification-worker` | ./services/notification-worker | — | postgres, redis, auth-service |
| `web` | node:20-alpine | 3000 | api-gateway |

All Python services mount their source directory as a volume and run with `--reload`, enabling hot-reload during development.

Health checks are defined for postgres (`pg_isready`) and redis (`redis-cli ping`). Dependent services use `condition: service_healthy` to ensure correct startup order.

**Start the full stack:**
```bash
./start.sh           # handles Docker/Colima automatically
./start.sh --build   # force image rebuild
./start.sh --fresh   # wipe database and start clean
```

### Kubernetes Manifests

**Directory:** `k8s/`

```
k8s/
├── 00-namespace.yaml              # splitease namespace
├── 01-configmap.yaml              # environment variables
├── 02-secrets.yaml                # sensitive values (base64)
├── ingress.yaml                   # NGINX ingress with path routing
├── api-gateway/
│   ├── deployment.yaml            # 2 replicas, liveness/readiness probes
│   ├── service.yaml               # ClusterIP
│   └── hpa.yaml                   # HPA: 2–5 replicas, 70% CPU target
├── auth-service/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
├── expense-service/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
├── notification-worker/
│   └── deployment.yaml            # 1 replica (stateful consumer)
├── postgres/
│   ├── statefulset.yaml           # persistent volume claim
│   └── service.yaml
├── redis/
│   ├── deployment.yaml
│   └── service.yaml
├── web/
│   ├── deployment.yaml
│   └── service.yaml
└── mailhog/                       # dev mail catcher
    ├── deployment.yaml
    └── service.yaml
```

**Key manifest features:**

- **HPA (Horizontal Pod Autoscaler)** on api-gateway, auth-service, and expense-service — scales between 2 and 5 replicas based on CPU utilisation (70% threshold).
- **Liveness and readiness probes** on all services — Kubernetes restarts unresponsive containers and withholds traffic from containers that are not yet ready.
- **ConfigMap + Secrets** separation — non-sensitive config in ConfigMap, credentials in Secrets.
- **StatefulSet** for PostgreSQL — ensures stable pod identity and persistent storage.
- **Ingress** routes `/api/*` to the gateway and `/` to the web frontend.

### Database Initialisation

**File:** `scripts/init-db.sql`

Creates both schemas and grants the application user the necessary privileges:
```sql
CREATE SCHEMA IF NOT EXISTS auth_schema;
CREATE SCHEMA IF NOT EXISTS expenses_schema;
GRANT ALL ON SCHEMA auth_schema TO splitease;
GRANT ALL ON SCHEMA expenses_schema TO splitease;
```

Alembic handles table creation and migrations within each service on startup.

### Environment Variables

**File:** `.env.example` (copy to `.env` for local dev)

| Variable | Used by | Description |
|---|---|---|
| `SECRET_KEY` | gateway, auth, expense | JWT signing key |
| `DATABASE_URL` | auth, expense, worker | PostgreSQL connection string |
| `REDIS_URL` | gateway, auth, expense, worker | Redis connection string |
| `AUTH_SERVICE_URL` | gateway, expense | Internal auth service base URL |
| `EXPENSE_SERVICE_URL` | gateway | Internal expense service base URL |
| `SMTP_HOST/PORT/USER/PASSWORD` | auth, worker | Email delivery |
| `FROM_EMAIL` | auth, worker | Sender address |
| `APP_URL` | worker | Frontend URL for notification deep links |
| `VAPID_PRIVATE_KEY` | worker | Web Push signing key |
| `VAPID_PUBLIC_KEY` | worker, frontend | Web Push public key |
| `VAPID_CLAIMS_EMAIL` | worker | VAPID claims subject |

---

*End of Report*
