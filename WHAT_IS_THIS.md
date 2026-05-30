# SplitEase — What Is This?

> A complete, production-grade expense-sharing application. Think Splitwise, built from scratch, running locally on Docker.

---

## The One-Liner

SplitEase lets a group of people add shared expenses, tracks who owes what to whom, simplifies those debts into the minimum number of payments, and notifies everyone in real time.

---

## What It Does (User Perspective)

1. **Register / Log in** — create an account, get a JWT token
2. **Create a group** — "Goa Trip", "Flat 4B", "Office Lunch Squad" — pick a currency (default ₹)
3. **Invite members** — add people by email
4. **Add an expense** — "₹1200 dinner, paid by Alice" → choose equal / exact / percentage split
5. **See balances** — who owes how much to whom, per group
6. **Simplify debts** — algorithm collapses N debts into the fewest possible payments (e.g. 6 debts → 2 payments)
7. **Record a settlement** — "Bob paid Alice ₹600" → balances update instantly
8. **Get notified** — browser push notification when someone adds an expense to your group

Everything works as a **PWA** — installable on phone, works offline for viewing.

---

## The Full Tech Stack

### Frontend
| | |
|---|---|
| **React 18 + TypeScript** | UI framework |
| **Vite** | Build tool (fast HMR in dev) |
| **Tailwind CSS** | Styling |
| **Zustand** | Global state (auth, offline queue) |
| **TanStack Query** | Server state, caching, pagination |
| **React Hook Form + Zod** | Forms with runtime type validation |
| **Axios** | HTTP client with auto camelCase↔snake_case conversion |
| **Workbox (PWA)** | Service worker, offline cache, background sync |
| **Framer Motion** | Animations |

### Backend (4 services, all Python + FastAPI)

| Service | Port | Owns |
|---|---|---|
| **API Gateway** | 8000 | Routing, JWT validation, rate limiting |
| **Auth Service** | 8001 | Users, passwords, tokens, push subscriptions |
| **Expense Service** | 8002 | Groups, expenses, settlements, balances |
| **Notification Worker** | — | Consumes Redis stream, sends push notifications |

Every service uses:
- **FastAPI** — async HTTP, auto Swagger UI at `/docs`
- **SQLAlchemy 2 (async)** — ORM with full async I/O
- **asyncpg** — PostgreSQL driver
- **Alembic** — database migrations
- **Pydantic v2** — request/response validation

### Data Layer
| | |
|---|---|
| **PostgreSQL 16** | Primary database (two schemas: `auth_schema`, `expenses_schema`) |
| **Redis 7** | Rate-limit counters, session tokens, Redis Streams event queue |

### Infrastructure / DevOps
| | |
|---|---|
| **Docker + Docker Compose** | Local dev stack (one command start) |
| **AWS ECS Fargate** | Production container orchestration |
| **AWS RDS** | Managed PostgreSQL in production |
| **AWS ElastiCache** | Managed Redis in production |
| **AWS S3 + CloudFront** | Frontend CDN |
| **Terraform** | All AWS infrastructure as code |
| **GitHub Actions** | CI/CD — build, push to ECR, deploy to ECS |

---

## System Architecture

```
Browser / PWA (React)
        │
        ├── static assets ──► CloudFront ──► S3
        │
        └── /api/* ──► API Gateway :8000
                           │  validates JWT
                           │  rate-limits (Redis)
                           │
                ┌──────────┴───────────┐
                ▼                      ▼
         Auth Service :8001     Expense Service :8002
         (users, tokens)        (groups, expenses,
                │                settlements, balances)
                │                      │
                └──────────┬───────────┘
                           ▼
                     PostgreSQL
                  auth_schema | expenses_schema
                           │
                           ▼
                     Redis Streams
                    (splitease:events)
                           │
                           ▼
                  Notification Worker
               (XREADGROUP → push/email)
```

---

## The 5 Interesting Technical Pieces

### 1. API Gateway — JWT Validation + Rate Limiting

The gateway validates the JWT itself (shared secret key) without asking the auth service — so every request only makes **one** downstream call, not two.

Rate limiting uses a Redis sliding-window counter keyed by IP (anonymous) or user ID (authenticated):
- Anonymous: 100 req/min
- Authenticated: 500 req/min

If the downstream service is down, the **circuit breaker** trips after 3 failures. Further requests are rejected immediately (fast-fail) for 30 seconds, then a single probe is allowed through. This prevents a slow downstream from exhausting the gateway's connection pool.

```
See it:  http://localhost:8000/health/breakers
Demo it: ./demo-circuit-breaker.sh
```

### 2. Debt Simplification Algorithm

Imagine 4 people in a group with 10 expenses. The naive approach gives you up to 12 (N×(N-1)) individual debts. The algorithm in `expense-service/utils/debt_simplification.py` runs a greedy net-balance approach:

1. Compute each person's net balance (positive = owed money, negative = owes money)
2. Sort into creditors (positive) and debtors (negative)
3. Greedily match the largest debtor to the largest creditor

Result: **minimum number of transactions** to settle the whole group. 6 debts might become 2 payments.

```
See it:  Group Detail → "Debts" tab
```

### 3. Redis Streams Message Queue

When Alice adds an expense, the expense-service calls:
```
XADD splitease:events * type expense.created expense_id <uuid> group_id <uuid> ...
```

The notification-worker runs a consumer group loop:
```
XREADGROUP GROUP splitease-notifications worker-1 COUNT 10 BLOCK 5000 STREAMS splitease:events >
```

It processes the event, sends a push notification to every group member except Alice, then:
```
XACK splitease:events splitease-notifications <message-id>
```

**Why this matters:** messages survive worker restarts (un-ACK'd messages replay from the beginning), multiple workers can share load, and expense-service has zero knowledge of the notification-worker.

```
Demo it: ./demo-message-queue.sh
```

### 4. Multi-Currency Support

Groups are denominated in a single currency (INR by default). But the same user can be in multiple groups with different currencies (INR group + USD group).

**The bug that was there and is now fixed:** the dashboard used to add ₹3,000 + $50 and show `$3,050.00`. It now computes balances per currency and displays each currency on its own line.

**Another fixed bug:** settling a ₹500 debt used to accidentally clear a $500 split. The settlement query now filters `WHERE expense.currency = settlement.currency`.

### 5. Offline-First PWA

The frontend is a Progressive Web App with a Workbox service worker. If you lose connectivity:

- **Viewing** groups and expenses still works (stale-while-revalidate cache)
- **Adding** an expense gets queued in IndexedDB via Zustand's `offlineStore`
- When you come back online, the queue replays automatically
- Push notifications arrive even when the app is closed (VAPID Web Push)

---

## How to Run It

```bash
# Start everything (handles Colima/Docker Desktop automatically)
./start.sh

# Force rebuild after code changes
./start.sh --build

# Wipe the database and start clean
./start.sh --fresh

# Stop everything
./start.sh --down

# Tail logs
./start.sh --logs
```

Once running:

| URL | What |
|---|---|
| http://localhost:3000 | The app |
| http://localhost:8000/health | Gateway health |
| http://localhost:8000/health/breakers | Circuit breaker state |
| http://localhost:8001/docs | Auth service Swagger UI |
| http://localhost:8002/docs | Expense service Swagger UI |

---

## Demo Scripts

Three interactive demos, each runs in ~1 minute:

```bash
# Shows: circuit breaker CLOSED → OPEN → HALF-OPEN → CLOSED
./demo-circuit-breaker.sh

# Shows: XADD → XREADGROUP → XACK full lifecycle with real data
./demo-message-queue.sh

# Shows: Kubernetes self-healing (pod killed → restarted automatically)
./demo-k8s-self-healing.sh
```

---

## Database Layout

Two schemas in one PostgreSQL instance (logical isolation, shared instance):

```
auth_schema
├── users               (id, email, name, hashed_password, avatar_url)
└── push_subscriptions  (user_id, endpoint, p256dh, auth_key)

expenses_schema
├── groups              (id, name, currency, created_by)
├── group_members       (group_id, user_id, role)
├── expenses            (id, group_id, amount, currency, paid_by, split_type, date)
├── expense_splits      (expense_id, user_id, share_amount, owed_amount, settled_at)
├── settlements         (group_id, paid_by, paid_to, amount, currency)
└── recurring_expenses  (group_id, amount, frequency, next_due)
```

Services never do cross-schema JOINs. The expense-service calls `GET /internal/users?ids=[...]` on the auth-service to enrich user data.

---

## Project Structure

```
College Project/
├── apps/web/                   React + Vite frontend
│   └── src/
│       ├── pages/              Route-level components (Dashboard, Groups, etc.)
│       ├── components/         Reusable UI (ExpenseCard, BalanceCard, etc.)
│       ├── api/                Axios API clients per domain
│       ├── hooks/              TanStack Query hooks (useExpenses, useGroups, etc.)
│       ├── store/              Zustand stores (auth, offline queue)
│       └── lib/                Utilities (formatCurrency, debt helpers)
│
├── services/
│   ├── api-gateway/            FastAPI — proxy, JWT auth middleware, rate limiter, circuit breaker
│   ├── auth-service/           FastAPI — register, login, JWT, bcrypt, push subscriptions
│   ├── expense-service/        FastAPI — groups, expenses, settlements, debt simplification
│   └── notification-worker/    Async worker — Redis stream consumer, push/email sender
│
├── infrastructure/terraform/   AWS VPC, ECS, RDS, ElastiCache, S3, CloudFront, ECR
├── k8s/                        Kubernetes manifests (deployments, services, HPA, ingress)
├── scripts/
│   ├── init-db.sql             Schema creation
│   └── seed.py                 Sample data seeder
│
├── docker-compose.yml          Full local stack
├── start.sh                    Failproof launcher (handles Colima/Docker Desktop)
├── demo-circuit-breaker.sh     Live circuit breaker demo
├── demo-message-queue.sh       Live Redis Streams demo
└── demo-k8s-self-healing.sh    Live Kubernetes self-healing demo
```

---

## Design Decisions (Quick Version)

**One PostgreSQL instance, two schemas** — not one DB per service. At this scale, separate databases would cost 3× more (~₹9,000/month on AWS instead of ~₹3,000) and add operational complexity for no real isolation benefit. The schemas are separated so migration to full isolation later is straightforward.

**Redis Streams, not RabbitMQ/Kafka** — Redis is already in the stack for rate limiting. Streams give us durable, consumer-group-based message delivery with zero extra infrastructure. For the notification volume of a college project, this is entirely sufficient.

**FastAPI, not Django/Flask** — native async/await means true non-blocking I/O. Auto-generated Swagger UI means every service is self-documenting. Pydantic v2 gives runtime validation and TypeScript-compatible schemas.

**Vite + React SPA, not Next.js** — the app is fully behind authentication so SSR buys nothing. A static SPA deploys to S3 + CloudFront for near-zero cost with no server to manage.

**JWT (15 min) + Redis-backed refresh tokens (7 days)** — short-lived access tokens limit blast radius if stolen. Refresh tokens are stored in Redis so they can be revoked server-side (logout actually works, unlike pure JWT).
