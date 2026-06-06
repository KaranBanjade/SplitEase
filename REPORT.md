# SplitEase — Project Report

**Course Project | Microservices Architecture**

---

## Table of Contents

1. [Core Principle](#1-core-principle)
2. [Domain Description](#2-domain-description)
3. [The Four Services](#3-the-four-services)
4. [System Architecture Diagram](#4-system-architecture-diagram)
5. [Communication Flows](#5-communication-flows)
6. [Architectural Decisions](#6-architectural-decisions)
7. [Source Code & Deployment Artifacts](#7-source-code--deployment-artifacts)
8. [Docker: Before and After](#8-docker-before-and-after)
9. [Failure Demonstrations](#9-failure-demonstrations)

---

## 1. Core Principle

**The guiding principle behind SplitEase is the Single Responsibility Principle (SRP) applied at the service level.**

Every service owns exactly one bounded context and is solely responsible for the data and logic within that context. No other service may read from or write to another service's data store — all cross-service access must go through a published API. This principle was the first decision made, and every subsequent design choice (service boundaries, communication style, database schema layout) was evaluated against it.

### Why SRP at the Service Level?

In a monolithic architecture, a shared-expense app would have a single codebase where the auth logic, financial logic, and notification logic are interleaved. A bug fix in the notification scheduler risks breaking the expense calculator. A performance optimisation on the user table requires a full application redeploy.

Applying SRP at the service level breaks those dependencies:

| Problem in a monolith | How SRP at service level solves it |
|---|---|
| A change to auth requires redeploying the whole app | Auth service deploys independently — other services are unaffected |
| Notification slowness blocks API responses | Notification worker is isolated; expense creation returns immediately |
| Scaling the expense calculator also scales the auth service | Each service scales independently based on its own load |
| A schema migration for expenses locks the user table | Schemas are owned per-service; no cross-service table locks |

### How It Is Demonstrated

| Service | Its Sole Responsibility |
|---|---|
| **API Gateway** | Traffic management — authentication, rate limiting, routing, aggregation |
| **Auth Service** | Identity — user accounts, tokens, password resets, push subscriptions |
| **Expense Service** | Financial data — groups, expenses, splits, balances, settlements |
| **Notification Worker** | Delivery — push notifications, email digests, scheduled reminders |

Each service has its own directory, its own `requirements.txt`, its own Dockerfile, and its own database schema. No service imports code from another. The only coupling is through well-defined HTTP contracts and the Redis Stream event schema.

---

## 2. Domain Description

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

## 3. The Four Services

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

## 4. System Architecture Diagram

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

## 5. Communication Flows

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

## 6. Architectural Decisions

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

## 7. Source Code & Deployment Artifacts

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

**Base image choice — `python:3.12-slim`**

All four Python services use `python:3.12-slim` as their base image. The decision is deliberate:

| Option | Size | Why rejected / chosen |
|---|---|---|
| `python:3.12` (full) | ~1 GB | Includes compilers, test tools, documentation — none needed at runtime |
| `python:3.12-slim` | ~130 MB | Strips non-essential packages; retains `pip` and the C runtime needed by `psycopg2` / `bcrypt` |
| `python:3.12-alpine` | ~50 MB | Uses `musl` libc; `psycopg2` and several cryptographic packages require `glibc` and fail to build cleanly on Alpine without custom compilation steps |
| `distroless/python3` | ~50 MB | No shell — complicates `apt-get install libpq-dev gcc` needed by `psycopg2` |

`python:3.12-slim` hits the sweet spot: small enough to keep pull times fast, compatible with all dependencies without workarounds, and still has a shell for `apt-get` during the build stage.

The `RUN apt-get install -y libpq-dev gcc` line installs the PostgreSQL client headers and C compiler needed to compile `psycopg2` from source. These are build-time only; a multi-stage build could exclude them from the final image, but the size saving (~15 MB) does not justify the added Dockerfile complexity at this scale.

**Frontend — `node:20-alpine`**

The web service uses `node:20-alpine`. Node's Alpine image does not have the `glibc` compatibility issues that affect Python's C-extension packages — the Vite build process is pure JavaScript, so Alpine is safe and halves the image size compared to `node:20-slim`.

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

### Container Registry — Docker Hub

Each service image is built, tagged, and pushed to Docker Hub under the `splitease` organisation. The Kubernetes manifests reference these published images so that the cluster never needs to build from source.

**Tagging strategy:**

```
splitease/api-gateway:latest
splitease/auth-service:latest
splitease/expense-service:latest
splitease/notification-worker:latest
splitease/web:latest
```

`latest` is used for the college demo. A production pipeline would replace this with a Git commit SHA tag (e.g. `splitease/api-gateway:9e3350a`) to make every deployment fully reproducible and auditable.

**Build and push workflow (per service):**

```bash
# Build
docker build -t splitease/api-gateway:latest ./services/api-gateway

# Authenticate
docker login

# Push
docker push splitease/api-gateway:latest
```

**Kubernetes manifests reference the registry images:**

```yaml
# k8s/api-gateway/deployment.yaml (excerpt)
containers:
  - name: api-gateway
    image: splitease/api-gateway:latest
    imagePullPolicy: Always
```

`imagePullPolicy: Always` ensures the cluster pulls the latest image on every pod restart, which is appropriate for `latest`-tagged images during iterative development. For production tagged releases, `IfNotPresent` would be used instead to avoid unnecessary pulls.

---

## 8. Docker: Before and After

This section demonstrates concretely how Docker resolves the deployment complexity that exists when running the application natively.

### Without Docker — Manual Setup

To run SplitEase without Docker, a developer must complete every step below on their machine before writing a single line of code:

**Step 1 — Install system dependencies**

```bash
# macOS
brew install postgresql@16 redis python@3.12 node@20

# Ubuntu
sudo apt-get install postgresql-16 redis-server python3.12 python3.12-venv nodejs npm libpq-dev gcc
```

This step differs across macOS, Ubuntu, Windows (WSL), and different distro versions. A developer on Ubuntu 22.04 gets PostgreSQL 14 by default from `apt` — not version 16. They must add the PostgreSQL apt repository manually, or the database behaviour may differ from production.

**Step 2 — Start and configure services**

```bash
# Start PostgreSQL and Redis as system services
sudo systemctl start postgresql
sudo systemctl start redis

# Create the database user and database
sudo -u postgres psql -c "CREATE USER splitease WITH PASSWORD 'yourpassword';"
sudo -u postgres psql -c "CREATE DATABASE splitease OWNER splitease;"
sudo -u postgres psql -d splitease -f scripts/init-db.sql
```

**Step 3 — Create Python virtual environments (once per service)**

```bash
cd services/api-gateway  && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && deactivate
cd services/auth-service  && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && deactivate
cd services/expense-service && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && deactivate
cd services/notification-worker && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && deactivate
cd apps/web && npm install
```

**Step 4 — Create and populate environment files**

Each service reads its configuration from environment variables. Without Docker's `environment:` block, the developer must create `.env` files manually in each service directory and fill in the correct values — database URLs, Redis URL, secret keys, SMTP credentials, VAPID keys.

**Step 5 — Run all services in separate terminals**

```bash
# Terminal 1
cd services/api-gateway && source .venv/bin/activate
uvicorn main:app --port 8000 --reload

# Terminal 2
cd services/auth-service && source .venv/bin/activate
uvicorn main:app --port 8001 --reload

# Terminal 3
cd services/expense-service && source .venv/bin/activate
uvicorn main:app --port 8002 --reload

# Terminal 4
cd services/notification-worker && source .venv/bin/activate
python main.py

# Terminal 5
cd apps/web && npm run dev
```

**Problems with this approach:**

| Problem | Impact |
|---|---|
| Version pinning is manual | Developer A has Python 3.11, Developer B has 3.12 — subtle runtime differences |
| Startup order is manual | Starting expense-service before auth-service is ready causes a connection error at boot |
| Environment variables are scattered | Each service has its own `.env`; keeping them consistent is error-prone |
| Port conflicts | PostgreSQL may already be running on the machine on port 5432 |
| Works on my machine | A missing system library (`libpq-dev`, `gcc`) causes `pip install` to fail on some machines |
| No isolation | Installing dependencies for this project modifies the global system Python or Node environment |
| Cleanup is manual | Stopping all services requires killing five terminal processes; leftover system services keep consuming memory |
| Onboarding time | A new developer must follow all five steps — typically 30–60 minutes with debugging |

---

### With Docker — One Command

Docker eliminates every problem above. The entire stack starts with:

```bash
./start.sh
```

or equivalently:

```bash
docker compose up --build
```

**What Docker Compose does automatically:**

| Manual step | Docker Compose equivalent |
|---|---|
| Install PostgreSQL 16 | `image: postgres:16-alpine` — exact version, every time |
| Install Redis 7 | `image: redis:7-alpine` |
| Create venvs and install packages | `RUN pip install -r requirements.txt` inside Dockerfile |
| Create DB user and schemas | `POSTGRES_USER`, `POSTGRES_DB` env vars + `init-db.sql` mounted as init script |
| Set environment variables | `environment:` block in `docker-compose.yml` |
| Start services in correct order | `depends_on: condition: service_healthy` — postgres and redis must pass health checks before any app service starts |
| Run all services | One `docker compose up` command |

**After-state:**

```
$ ./start.sh
[+] Running 7/7
 ✔ Container splitease-postgres-1           Healthy
 ✔ Container splitease-redis-1              Healthy
 ✔ Container splitease-auth-service-1       Started
 ✔ Container splitease-expense-service-1    Started
 ✔ Container splitease-api-gateway-1        Started
 ✔ Container splitease-notification-worker-1 Started
 ✔ Container splitease-web-1               Started

Frontend: http://localhost:3000
API:      http://localhost:8000
```

All services are running, correctly ordered, with consistent versions, in under 60 seconds on a fresh clone — regardless of what is installed on the developer's machine. The only prerequisite is Docker Desktop.

**Teardown is equally simple:**

```bash
docker compose down          # stop and remove containers
docker compose down -v       # also wipe database volumes (./start.sh --fresh)
```

### Summary: Complexity Comparison

| Dimension | Without Docker | With Docker |
|---|---|---|
| **Prerequisites** | PostgreSQL, Redis, Python 3.12, Node 20, system libs | Docker Desktop only |
| **Setup time (new machine)** | 30–60 min | < 2 min |
| **Version consistency** | Depends on developer's installed versions | Pinned in `docker-compose.yml` |
| **Startup order** | Manual | `depends_on: condition: service_healthy` |
| **Env var management** | 5 separate `.env` files | One `docker-compose.yml` |
| **Isolation** | Pollutes global Python/Node env | Each container is isolated |
| **Reproducibility** | "Works on my machine" risk | Identical environment everywhere |
| **Onboarding command** | 5-step manual process | `./start.sh` |

---

## 9. Failure Demonstrations

### 9a — Circuit Breaker Tripping

The circuit breaker is implemented in `services/api-gateway/proxy.py` as `AsyncCircuitBreaker`. It wraps every outbound `httpx` call to a downstream service.

**Setup:** Start the full stack, then simulate an auth-service failure:

```bash
# Start everything
./start.sh

# In a second terminal, stop the auth service to simulate a crash
docker compose stop auth-service
```

**What happens — request flow before the breaker opens:**

```
Client                  API Gateway             Auth Service (DOWN)
  │                          │                        │
  │  POST /api/auth/login     │                        │
  │─────────────────────────►│                        │
  │                          │  POST /auth/login       │
  │                          │───────────────────────►│ ← ConnectError (1st failure)
  │                          │  POST /auth/login       │
  │                          │───────────────────────►│ ← ConnectError (2nd failure)
  │                          │  POST /auth/login       │
  │                          │───────────────────────►│ ← ConnectError (3rd failure)
  │                          │                        │
  │                          │  [BREAKER OPENS]        │
```

**What happens — breaker is open:**

```
Client                  API Gateway
  │                          │
  │  POST /api/auth/login     │
  │─────────────────────────►│
  │                          │  Breaker state: OPEN
  │                          │  (no HTTP call made)
  │  HTTP 503                │
  │  {"detail": "auth-service unavailable"}
  │◄─────────────────────────│
  │                          │  ← returned in microseconds
```

The gateway returns HTTP 503 immediately without attempting the downstream call. This prevents the gateway's connection pool from being exhausted by slow timeouts while auth-service is restarting.

**Recovery — half-open probe:**

After 30 seconds, the breaker transitions to **half-open** and allows one probe request through:

```bash
# Restart auth-service
docker compose start auth-service
```

```
Client                  API Gateway             Auth Service (UP)
  │                          │                        │
  │  POST /api/auth/login     │  [HALF-OPEN — probe]  │
  │─────────────────────────►│───────────────────────►│
  │                          │  200 OK                │
  │                          │◄───────────────────────│
  │  200 OK                  │  [BREAKER CLOSES]       │
  │◄─────────────────────────│                        │
```

The breaker closes and normal traffic resumes. Subsequent requests flow through without restriction.

**Observable output (API Gateway logs):**

```
INFO:     Circuit breaker for auth-service: CLOSED → OPEN (3 consecutive failures)
INFO:     Circuit breaker for auth-service: rejecting request — state OPEN
INFO:     Circuit breaker for auth-service: OPEN → HALF-OPEN (30s elapsed)
INFO:     Circuit breaker for auth-service: probe succeeded — HALF-OPEN → CLOSED
```

---

### 9b — Kubernetes Self-Healing

Kubernetes automatically restarts pods that crash or are killed. This is governed by the `restartPolicy: Always` on each Deployment.

**Setup:** Deploy to a local Kubernetes cluster (e.g. Docker Desktop Kubernetes or minikube):

```bash
kubectl apply -f k8s/
```

**Verify all pods are running:**

```bash
kubectl get pods -n splitease
```

```
NAME                                    READY   STATUS    RESTARTS   AGE
api-gateway-7d9f8b6c4-x2kpj            1/1     Running   0          5m
api-gateway-7d9f8b6c4-m8rvt            1/1     Running   0          5m
auth-service-6c8b9d7f5-p4nqw           1/1     Running   0          5m
expense-service-5f7d6c8b9-k3lmx        1/1     Running   0          5m
notification-worker-4b8c7d6f5-r2stv    1/1     Running   0          5m
postgres-0                             1/1     Running   0          5m
redis-7c6b9f8d4-w5xyz                  1/1     Running   0          5m
```

**Kill a pod manually:**

```bash
kubectl delete pod auth-service-6c8b9d7f5-p4nqw -n splitease
```

**Watch Kubernetes respond:**

```bash
kubectl get pods -n splitease --watch
```

```
NAME                                    READY   STATUS        RESTARTS   AGE
auth-service-6c8b9d7f5-p4nqw           1/1     Terminating   0          5m
auth-service-6c8b9d7f5-p4nqw           0/1     Terminating   0          5m
auth-service-6c8b9d7f5-j9abc           0/1     Pending       0          0s    ← new pod
auth-service-6c8b9d7f5-j9abc           0/1     ContainerCreating  0     1s
auth-service-6c8b9d7f5-j9abc           1/1     Running       0          8s    ← healthy
```

The pod is replaced within ~8 seconds. During this window, the API Gateway's circuit breaker absorbs the failure — returning HTTP 503 for auth requests rather than hanging — and then recovers automatically once the new pod passes its readiness probe.

**Readiness probe configuration (from `k8s/auth-service/deployment.yaml`):**

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 5
  periodSeconds: 5
livenessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 3
```

- The **readiness probe** prevents Kubernetes from sending traffic to the new pod until it responds HTTP 200 on `/health` — ensuring the database connection pool is established before real requests arrive.
- The **liveness probe** will restart a pod that becomes unresponsive mid-run (e.g. deadlock, OOM) even without a manual `kubectl delete`.

**Demonstrating liveness restart (simulate a hung process):**

```bash
# Exec into a pod and kill the uvicorn process
kubectl exec -it auth-service-6c8b9d7f5-j9abc -n splitease -- kill 1
```

```
NAME                                    READY   STATUS      RESTARTS   AGE
auth-service-6c8b9d7f5-j9abc           0/1     OOMKilled   1          2m
auth-service-6c8b9d7f5-j9abc           1/1     Running     1          2m10s
```

The `RESTARTS` counter increments to 1. Kubernetes automatically brought the container back up. If the pod crashes repeatedly in a short window, Kubernetes applies exponential back-off (CrashLoopBackOff) to prevent a rapid restart loop from consuming cluster resources.

---

*End of Report*
