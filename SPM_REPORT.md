# SplitEase — SPM Assignment Report
## Software Product Management | AY 2025–26

**Student**

| Name | Roll No. |
|---|---|
| Karan Banjade | 2023SL70034 |

---

## Table of Contents

**Part 1 — Pre Mid-Sem**
1. [Product Opportunity](#1-product-opportunity)
2. [Opportunity Assessment](#2-opportunity-assessment)
   - 2.1 [Customer Interviews](#21-customer-interviews)
   - 2.2 [Post-Interview Revision](#22-post-interview-revision)
   - 2.3 [Re-assessment](#23-re-assessment)
   - 2.4 [Final Product Idea & Value Proposition](#24-final-product-idea--value-proposition)
3. [Story Map](#3-story-map)
4. [Business Plan — Startup Canvas](#4-business-plan--startup-canvas)

**Part 2 — Post Mid-Sem**

5. [MVP Features](#5-mvp-features)
6. [Solutions — Low Fidelity Sketches](#6-solutions--low-fidelity-sketches)
7. [Wireframe Storyboard](#7-wireframe-storyboard)
8. [Validation — Customer Feedback](#8-validation--customer-feedback)
9. [Iteration — Revised Wireframes](#9-iteration--revised-wireframes)

---

---

# PART 1 — PRE MID-SEM

---

## 1. Product Opportunity

### Customer Segment

**College students and young working professionals (ages 18–28)** who share living spaces, travel together, or socialise in groups on a regular basis.

This segment is extremely familiar to me — I live in a shared PG and have personally experienced the friction of managing shared costs with flatmates and friends. I chose this segment because I interact with it daily and could interview real users quickly.

### The Problem

When a group of people shares costs — groceries, rent, restaurant bills, trip expenses, utility bills — someone always ends up paying first. Over time, debts accumulate across multiple people and multiple events. Tracking who owes whom becomes a chaotic mix of WhatsApp messages, screenshots, and mental arithmetic. Asking friends to "pay back" is socially awkward. Forgotten debts cause relationship friction.

### Underserved Needs

| Need | Current Workaround | Why it Fails |
|---|---|---|
| Know exactly who owes what at any point | WhatsApp notes, screenshots | Scattered, not updated in real time |
| Split unequal expenses fairly (e.g. bigger room pays more rent) | Manual calculation on calculator | Error-prone, not recorded |
| Remind someone without it being awkward | Nudging personally on chat | Causes friction, often ignored |
| Settle up quickly across multiple debts | Multiple bank transfers | Confusing, easy to under/overpay |
| Keep a record for future reference | None | No audit trail |

### The Product

**SplitEase** is a web-based shared expense tracking app. A group creates a shared space, members add expenses with a chosen split mode (equal, exact amount, or percentage), and the app calculates a simplified list of who needs to pay whom to settle all debts — with the minimum number of transactions. Members are notified when new expenses are added and receive weekly balance reminders.

### Pain Points

- Manually dividing bills causes mistakes and arguments
- No single place to track ongoing group debts
- Social awkwardness of chasing friends for money
- Multiple small debts pile up with no easy "settle all" path
- Existing tools (Splitwise) are feature-heavy and confusing for casual users

### Value Proposition

> *"Add an expense in 10 seconds. Know exactly who owes what. Settle with the fewest possible payments — without a single awkward conversation."*

---

## 2. Opportunity Assessment

### 2.1 Customer Interviews

I conducted 5 in-depth interviews over one week. Each interview was approximately 20–30 minutes and focused on the interviewee's current activities, daily frustrations, and how they currently manage shared costs.

---

#### Interview 1 — Rahul Nair, 3rd Year B.Tech Student, Shared PG (5 roommates)

**Interviewer:** Karan Banjade  
**Setting:** Common room of his PG, informal chat

**Background:** Rahul lives with 4 other roommates. They share groceries, a Netflix subscription, electricity, and occasional takeout. Rahul is the de facto "treasurer" because he has a UPI account that everyone transfers to.

**Key Observations from Activities:**
- Rahul manually maintains a WhatsApp group called "Flat Khata" where everyone posts when they spend money.
- At month-end he manually tallies everything in a notes app and announces "Karan owes 340, Rohit owes 560."
- He spends about 45–60 minutes per month doing this reconciliation.
- Two roommates consistently "forget" to pay, and Rahul finds it extremely awkward to ask them.

**Pain Points Surfaced:**
- "I basically run a part-time accounting job for free."
- "Sometimes I miss a message in the group chat and the numbers go wrong."
- "I don't want to be the bad guy who keeps asking for money."

**What he values:**
- An automatic tally he doesn't have to compute himself.
- The app itself sending reminders so he doesn't have to.
- Something that shows a clear "you owe / you are owed" summary instantly.

**Relevance to SplitEase:** Very high. Rahul is the exact primary user. The auto-debt simplification and push notification features directly address his top two pain points.

---

#### Interview 2 — Ananya Krishnan, 24, Junior Software Engineer, Lives with 2 Friends

**Interviewer:** Karan Banjade  
**Setting:** Video call

**Background:** Ananya works at a Bangalore startup and shares a flat with two college friends. They do 2–3 trips per year. During trips expenses explode: hotels, cabs, food, entry tickets, fuel.

**Key Observations from Activities:**
- During trips, Ananya uses a shared Google Sheet one of her friends created. Different columns for each person.
- After the trip it takes them 2–3 days to fully close the sheet and figure out who pays whom.
- During the trip nobody updates the sheet in real time because "there's no time."
- She uses Splitwise on her phone but says: "It has too many steps to add an expense. I give up halfway."

**Pain Points Surfaced:**
- The gap between expense happening and expense being recorded is where mistakes occur.
- The settlement step — figuring out the minimum set of transfers — is what takes the most time.
- The app's complexity is a real barrier.

**What she values:**
- Very fast expense entry — ideally under 3 taps.
- Automatic debt simplification without having to manually cross-cancel amounts.
- Works on mobile without needing to install an app (she prefers browser-based).

**Relevance to SplitEase:** High. Informed the decision to build a PWA (browser-installable) rather than a native app, and to prioritise the speed of expense creation.

**Post-interview adjustment:** Added a "quick add" flow with smart defaults (equal split, last used group) as a direct result of Ananya's feedback on Splitwise's complexity.

---

#### Interview 3 — Karan Bose, 2nd Year MBA, Monthly Friend Group Dinners

**Interviewer:** Karan Banjade  
**Setting:** Canteen

**Background:** Karan is part of a group of 8 friends who go out for dinner once a month. The bill is always split unevenly because some people order more, drink alcohol, etc. One person pays the bill and the others transfer.

**Key Observations from Activities:**
- They use WhatsApp to figure out who owes what. The payer sends a photo of the bill and everyone "mentally calculates" their share.
- Disputes happen regularly about whether service charge should be split equally or by consumption.
- Settlements are done via UPI but sometimes people transfer the wrong amounts.
- The group doesn't have a running balance — each dinner is treated independently, so small discrepancies never get corrected.

**Pain Points Surfaced:**
- "Every time we go out it's a 15-minute WhatsApp argument about the bill."
- "I paid extra last time and I know it, but there's no record so I can't bring it up."

**What he values:**
- Ability to see historical balance (cumulative across multiple events, not just one dinner).
- Exact split — where specific people are assigned specific amounts.
- A clean shareable summary he can send to the group.

**Relevance to SplitEase:** Medium-high. The "exact split" mode and per-group cumulative balance view are important to this persona. Shareable summaries were not in the initial plan — added to the backlog.

---

#### Interview 4 — Divya Menon, 22, Final Year Student, Hostel

**Interviewer:** Karan Banjade  
**Setting:** Library (quiet corner)

**Background:** Divya lives in a hostel and shares expenses primarily with her "study group" of 4 friends — stationery, shared food delivery orders, and printing costs.

**Key Observations from Activities:**
- Amounts are small but frequent. A typical debt is ₹30–₹80.
- Divya pays for things and never asks for it back because "it's too small and awkward."
- Over a semester, she estimated she absorbs ₹2,000–₹3,000 of shared costs she never recovered.
- She has tried Splitwise but felt it was "overkill" for small amounts.

**Pain Points Surfaced:**
- "Even small amounts add up. But it feels rude to ask for ₹40 back."
- "I need something that tracks it automatically so I can see the total and feel okay asking."
- "The reminder should come from the app, not from me."

**What she values:**
- Frictionless logging — quick enough to do in 30 seconds.
- Automated reminders so she never has to ask personally.
- Low formality — doesn't feel like using accounting software.

**Relevance to SplitEase:** High. Divya's profile pointed us toward the "casual, lightweight" positioning. Our initial design was too feature-heavy. We simplified the default UI and made notification reminders more prominent.

---

#### Interview 5 — Siddharth Rao, 26, Product Analyst, Frequent Traveler

**Interviewer:** Karan Banjade  
**Setting:** Coffee shop

**Background:** Siddharth travels with friends 4–5 times a year, trips ranging from weekend getaways to 10-day international trips. He has used Splitwise for 3 years.

**Key Observations from Activities:**
- Siddharth is a power user of Splitwise and knows its features well.
- His biggest complaint: "When we come back from a trip, Splitwise tells me I need to pay 4 different people. I have to do 4 UPI transfers. It's annoying."
- He values **debt simplification** — the ability to consolidate multiple debts into the minimum number of transfers.
- He also wants offline capability — "On a Ladakh trip there's no internet for days. I want to log expenses offline and sync later."

**Pain Points Surfaced:**
- Multi-person settlement is fragmented.
- No offline mode in most alternatives.
- Splitwise's free tier has become increasingly limited.

**What he values:**
- Debt simplification (minimum transactions to settle).
- Offline capability.
- Free product without feature walls.

**Relevance to SplitEase:** Very high. Siddharth validated debt simplification as a core feature, not just a nice-to-have. His offline requirement confirmed the PWA + service worker strategy. The "minimum transactions" algorithm became a headline feature.

---

### 2.2 Post-Interview Revision

**Original product idea:** A simple bill-splitting app where users add expenses and see who owes whom.

**Changes made after interviews:**

| Insight Source | Original Assumption | Revised Decision |
|---|---|---|
| Ananya — too many taps | Detailed expense form | Smart defaults (equal split, last group pre-selected) |
| Divya — feels like accounting software | Feature-rich dashboard | Clean, minimal default view; advanced features behind a tap |
| Siddharth — debt simplification is critical | Nice-to-have | Core feature, shown prominently on group page |
| Siddharth — offline capability | Not considered | PWA with service worker, offline queue |
| Karan — historical balance matters | Per-expense view only | Running group balance view added |
| Rahul — social awkwardness of reminders | Manual reminders | Automated push notification reminders sent by the app |

**Idea that was dropped:** In-app UPI payment integration. Interviews showed users are comfortable with existing UPI apps — they just need to know the *correct amount* to transfer. Building a payment gateway would add complexity without proportional value.

---

### 2.3 Re-assessment

After revisions, I re-assessed the idea against the interview findings:

| Criterion | Pre-interview | Post-interview |
|---|---|---|
| Core value clear to user? | Somewhat — "track expenses" | Yes — "know exactly who owes what, settle with minimum transfers" |
| Differentiation from Splitwise? | Weak | Stronger — faster entry, PWA/offline, simpler UX, free |
| Does it solve Rahul's pain? | Yes | Yes, more directly with auto-reminders |
| Does it solve Ananya's pain? | Partially | Yes, with 3-tap quick add and PWA |
| Does it solve Divya's pain? | Partially | Yes, with automated reminders and lighter UI |
| Offline support? | No | Yes, PWA + service worker |

**Conclusion:** The revised product has a clear, compelling value proposition for the target segment. All five interviewees confirmed they would use the app. Three said they would switch from their current solution immediately.

---

### 2.4 Final Product Idea & Value Proposition

#### Final Product: SplitEase

A browser-based Progressive Web App for shared expense tracking, built for college students and young adults sharing costs in groups.

#### Target Customer

**Primary:** College students living in shared accommodations (PGs, hostels, shared flats), aged 18–24, in Tier 1 and Tier 2 Indian cities.

**Secondary:** Young working professionals (24–30) who travel in groups or share apartments.

#### Underserved Need

The customer's core unmet need is: **frictionless, automatic reconciliation of shared costs without social awkwardness.** Current workarounds (WhatsApp notes, manual spreadsheets, Splitwise's complex UI) are either too slow to use in the moment or too complex to be adopted consistently.

#### Value Proposition (Product-Market Fit Pyramid — Bottom 3 Layers)

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: VALUE PROPOSITION                                     │
│                                                                 │
│  "Add an expense in 10 seconds. See who owes what instantly.   │
│   Settle with the fewest possible transfers.                   │
│   The app reminds your friends — so you don't have to."        │
│                                                                 │
│  Core differentiators:                                         │
│  • Debt simplification algorithm (minimum transactions)        │
│  • Automated push notification reminders                       │
│  • PWA — works offline, installable, no app store needed       │
│  • 3-tap expense entry with smart defaults                     │
└─────────────────────────────────────────────────────────────────┘
              ▲
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: UNDERSERVED NEED                                      │
│                                                                 │
│  Shared expense groups (flatmates, travel groups, friend        │
│  circles) have no lightweight, always-available tool that       │
│  automatically reconciles debts and removes the social          │
│  discomfort of asking friends to pay back.                      │
│                                                                 │
│  Current solutions are too slow, too complex, or too manual.   │
└─────────────────────────────────────────────────────────────────┘
              ▲
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: TARGET CUSTOMER                                       │
│                                                                 │
│  College students and young professionals (18–28) who share     │
│  costs regularly — accommodation, travel, dining — in groups    │
│  of 2–8 people. They are mobile-first, WhatsApp-native, and    │
│  prefer convenience over features.                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Story Map

The story map organises user activities (top row) into the tasks required to complete them, arranged from left to right in the order a new user would encounter them.

```
NARRATIVE:  New User  ──►  Set Up Group  ──►  Log Expenses  ──►  Track Balances  ──►  Settle Up  ──►  Stay Informed
            Joins App                                                                                   Over Time

────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
ACTIVITIES  │  ONBOARDING    │  GROUP SETUP      │  EXPENSE ENTRY     │  BALANCE VIEW      │  SETTLEMENT       │  NOTIFICATIONS
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
BACKBONE    │  Register /    │  Create group /   │  Add expense       │  View group        │  Record           │  Receive push
(must have) │  Login         │  Join via link    │  (equal split)     │  balance           │  payment          │  notification
────────────┼────────────────┼───────────────────┼────────────────────┼────────────────────┼───────────────────┼──────────────
RELEASE 1   │  Email+pass    │  Name group       │  Title + amount    │  "You are owed"    │  Select payer     │  Expense added
(MVP)       │  registration  │  Add members      │  Select payer      │  / "You owe"       │  + payee          │  notification
            │                │  by email         │  Equal split       │  summary           │  + amount         │
            │                │                   │  Confirm           │  Per-person        │  Confirm          │
            │                │                   │                    │  balance list      │                   │
────────────┼────────────────┼───────────────────┼────────────────────┼────────────────────┼───────────────────┼──────────────
RELEASE 2   │  Profile pic   │  Edit group name  │  Exact split       │  Simplified debt   │  Settlement       │  Weekly
(V1.1)      │  / display     │  / description    │  (per-person       │  graph —           │  history          │  balance
            │  name          │  Remove member    │  amounts)          │  minimum txns      │  per group        │  digest email
            │                │                   │  Percentage split  │  Expense history   │                   │  reminder push
            │                │                   │  Add notes         │  (scrollable)      │                   │
────────────┼────────────────┼───────────────────┼────────────────────┼────────────────────┼───────────────────┼──────────────
RELEASE 3   │  Social login  │  Group categories │  Recurring         │  Export to PDF     │  Partial          │  Settlement
(V1.2)      │  (Google)      │  (trip/flat/other)│  expenses          │  / CSV             │  settlement       │  reminders
            │  Offline mode  │  Group avatar     │  Photo receipt     │  Multi-currency    │  support          │  for old debts
            │                │                   │  attach            │  support           │                   │
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
```

**Reading the story map:**
- The top row (Activities) represents what the user is trying to accomplish.
- The Backbone row contains the minimum tasks for each activity to be functional.
- Releases 1–3 represent progressive delivery slices — each row is a shippable increment.
- Release 1 (MVP) can be cut horizontally and delivered independently.

---

## 4. Business Plan — Startup Canvas

```
┌───────────────────────────┬──────────────────────────┬────────────────────────────────────────┐
│  PROBLEM                  │  SOLUTION                │  UNIQUE VALUE PROPOSITION              │
│                           │                          │                                        │
│  1. Tracking shared       │  SplitEase — a PWA that  │  "The only expense splitter fast       │
│     expenses manually     │  lets groups log, split, │  enough to use at the dinner table     │
│     is slow and error-    │  and settle shared       │  and smart enough to minimise your     │
│     prone                 │  expenses:               │  settlement transfers."                │
│                           │                          │                                        │
│  2. Asking friends for    │  • 3-tap expense entry   │  For: College students and young       │
│     money is socially     │  • Auto debt             │  professionals sharing costs           │
│     awkward               │    simplification        │                                        │
│                           │  • Push reminders        │  Unlike Splitwise (complex, paywalled) │
│  3. Existing tools        │  • Works offline         │  SplitEase is fast, free, and          │
│     (Splitwise) are       │                          │  browser-native                        │
│     too complex /         │                          │                                        │
│     feature-gated         │                          │                                        │
├───────────────────────────┴──────────────────────────┤                                        │
│  EXISTING ALTERNATIVES                               │                                        │
│  • WhatsApp notes / screenshots                      │                                        │
│  • Google Sheets                                     │                                        │
│  • Splitwise (free tier limited)                     │                                        │
│  • IOU (limited features)                            │                                        │
├──────────────────────────────────────────────────────┴────────────────────────────────────────┤
│  KEY METRICS                        │  CHANNELS                                               │
│                                     │                                                         │
│  • Daily Active Users (DAU)         │  • College WhatsApp groups (organic sharing)            │
│  • Expenses logged per day          │  • Word of mouth — one user invites group               │
│  • Groups created per week          │  • Instagram / LinkedIn student communities             │
│  • D7 / D30 retention rate          │  • College fests and hostel notice boards               │
│  • Push notification opt-in rate    │  • Reddit (r/india, r/developersIndia)                  │
│  • Settlement conversion rate       │                                                         │
├─────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│  COST STRUCTURE                     │  REVENUE STREAMS                                        │
│                                     │                                                         │
│  • AWS hosting: ~₹2,500/mo          │  Phase 1 (Year 1): Free — grow user base                │
│    (ECS Fargate + RDS + ElastiCache)│                                                         │
│  • Domain + SSL: ~₹1,000/yr         │  Phase 2 (Year 2): SplitEase Pro — ₹99/mo              │
│  • SMTP email service: ~₹500/mo     │  • Unlimited groups                                    │
│  • Development: team effort         │  • Export to PDF/CSV                                   │
│                                     │  • Priority reminders                                  │
│  Total burn: ~₹4,000/mo (seed phase)│  • Ad-free                                             │
│                                     │                                                         │
│                                     │  Phase 3: B2B (corporate teams, event organisers)      │
├─────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│  KEY ADVANTAGES                     │  CUSTOMER SEGMENTS                                      │
│                                     │                                                         │
│  • Built by the target users —      │  Primary: College students in shared PGs /              │
│    deep understanding of pain       │  hostels (India, 18–24, Tier 1 + Tier 2 cities)        │
│  • No payment gateway complexity    │                                                         │
│  • PWA = no app store friction      │  Secondary: Young working professionals                 │
│  • Debt simplification algo is      │  sharing flats or travelling together (24–30)          │
│    technically non-trivial —        │                                                         │
│    hard to replicate quickly        │  Tertiary: Small teams / project groups                 │
│  • Fully open source — builds trust │  tracking shared purchases                             │
└─────────────────────────────────────┴─────────────────────────────────────────────────────────┘
```

---

---

# PART 2 — POST MID-SEM

---

## 5. MVP Features

Based on the story map (Release 1) and customer interview findings, the following MVP features were defined:

### MVP Feature List

| # | Feature | Why it is MVP |
|---|---|---|
| 1 | **User Registration & Login** (email + password) | Gate to the product. Without identity, no group, no expense. JWT-based so sessions persist. |
| 2 | **Create a Group / Join via invite** | The atomic unit of SplitEase. All subsequent features are within a group context. |
| 3 | **Add an Expense (equal split only)** | The most common use case from all 5 interviews. Equal split covers ~70% of real scenarios. |
| 4 | **View Group Balance** ("You owe / You are owed" summary) | The primary output users care about. Without this, there is no reason to log expenses. |
| 5 | **Simplified Debt View** (minimum transactions) | Validated by Siddharth as critical. A direct competitive advantage over WhatsApp-based solutions. |
| 6 | **Record a Settlement** | Closes the loop — without settlements, balances only grow and the app becomes useless over time. |
| 7 | **Push Notification on New Expense** | Validated by Rahul and Divya as the feature that removes social awkwardness. Core to the value prop. |

### Features Deliberately Excluded from MVP

| Feature | Reason for Deferral |
|---|---|
| Exact / Percentage split | Added complexity without covering the 80% case. Can ship in v1.1. |
| Recurring expenses | Niche feature; adds significant backend complexity. v1.2. |
| Email digests | Nice to have; push notifications already solve the reminder problem. v1.1. |
| Export / PDF | Used rarely; adds UI work disproportionate to value at launch. v1.2. |
| Google / Social login | Simplifies onboarding but not blocking for launch. v1.1. |
| Offline mode | Important but technically complex (service worker, sync queue). v1.1. |

---

## 6. Solutions — Low Fidelity Sketches

I independently sketched 4 distinct design approaches on paper, each starting from a different mental model of what the "home screen" should prioritise. After completing all 4 sketches, I evaluated each one and identified the standout ideas across them before selecting a direction.

---

### Approach A — "Activity Feed First"

**Design philosophy:** The home screen shows a chronological feed of all recent activity across all groups — similar to a social media timeline. Users see what happened, tap to act.

```
┌─────────────────────────┐
│  SplitEase         [+]  │
│  ─────────────────────  │
│  📍 All Activity        │
│                         │
│  ┌─────────────────┐    │
│  │ Arjun added     │    │
│  │ "Groceries ₹480"│    │
│  │ Flat Group  2h  │    │
│  │ You owe ₹120 ↗  │    │
│  └─────────────────┘    │
│  ┌─────────────────┐    │
│  │ Priya settled   │    │
│  │ ₹200 with you   │    │
│  │ Trip Group  5h  │    │
│  └─────────────────┘    │
│                         │
│  [Groups] [You Owe ₹320]│
└─────────────────────────┘
```

**Standout ideas identified:**
- ⭐ "You owe ₹320" total balance pinned at bottom — *(strong signal from interviews; Rahul and Ananya both mentioned wanting a single summary number)*
- ⭐ Activity feed shows both expenses AND settlements in one view — *(reduces need to switch tabs)*

---

### Approach B — "Group Card Dashboard"

**Design philosophy:** Home screen shows cards for each group. Each card shows the group name, member count, and the user's current balance in that group at a glance. Tap to go deeper.

```
┌─────────────────────────┐
│  Hi Arjun 👋       [+]  │
│  You owe ₹320 total     │
│  ─────────────────────  │
│  ┌──────────────────┐   │
│  │ 🏠 Flat B-204    │   │
│  │ 4 members        │   │
│  │ You owe  ₹240  → │   │
│  └──────────────────┘   │
│  ┌──────────────────┐   │
│  │ ✈️ Goa Trip      │   │
│  │ 3 members        │   │
│  │ You owe   ₹80  → │   │
│  └──────────────────┘   │
│  ┌──────────────────┐   │
│  │ 🍕 Lunch Crew    │   │
│  │ 6 members        │   │
│  │ You are owed ₹0  │   │
│  └──────────────────┘   │
└─────────────────────────┘
```

**Standout ideas identified:**
- ⭐⭐⭐ Group card with balance-at-a-glance without tapping in — *(most aligned with what interviewees wanted: "know where I stand immediately")*
- ⭐ Total "you owe" across all groups shown prominently on home — *(recurring request across 4 of 5 interviews)*

---

### Approach C — "Settle-First Design"

**Design philosophy:** Rohan flipped the focus — instead of showing expenses, show the end state: what you need to do. Home screen = list of people you owe / who owe you, with a "Settle" button on each.

```
┌─────────────────────────┐
│  Settle Up         [+]  │
│  ─────────────────────  │
│  YOU OWE                │
│  ┌──────────────────┐   │
│  │ → Rahul   ₹240   │   │
│  │   Flat B-204     │   │
│  │          [Settle]│   │
│  └──────────────────┘   │
│  ┌──────────────────┐   │
│  │ → Ananya   ₹80   │   │
│  │   Goa Trip       │   │
│  │          [Settle]│   │
│  └──────────────────┘   │
│  ─────────────────────  │
│  OWED TO YOU            │
│  Priya owes you  ₹150   │
│  Karan owes you   ₹60   │
└─────────────────────────┘
```

**Standout ideas identified:**
- ⭐⭐ Settle button directly on the balance row — no navigation needed — *(Siddharth specifically said "I hate how many taps it takes to settle in Splitwise")*

---

### Approach D — "Conversational Add"

**Design philosophy:** Adding an expense should feel like sending a message, not filling a form. Neha's sketch shows an inline "expense composer" at the bottom of the screen — like a chat input.

```
┌─────────────────────────┐
│  Flat B-204        [⚙]  │
│  ─────────────────────  │
│  Balances:              │
│  Rahul   owes you ₹140  │
│  Karan   owes you  ₹80  │
│  You   owe Priya   ₹60  │
│  ─────────────────────  │
│  Recent:                │
│  Groceries   ₹480  2d   │
│  Electricity ₹360  1w   │
│  ─────────────────────  │
│  ┌──────────────────┐   │
│  │ What did you pay?│   │
│  │ [Groceries  ][₹] │   │
│  │ [Equal ▼] [Add]  │   │
│  └──────────────────┘   │
└─────────────────────────┘
```

**Standout ideas identified:**
- ⭐⭐⭐ Inline expense composer — no modal, no navigation — *(Ananya said "Splitwise has too many steps"; Divya said "I need it in 30 seconds"; this directly addresses both)*

---

### Standout Ideas Summary

| Idea | Strength | Source |
|---|---|---|
| Group card with balance-at-a-glance | ⭐⭐⭐ Highest | Approach B |
| Inline expense composer | ⭐⭐⭐ Highest | Approach D |
| Settle button on balance row | ⭐⭐ High | Approach C |
| Total "you owe" pinned on home | ⭐ Medium | Approach A + B |
| Activity feed (expenses + settlements) | ⭐ Medium | Approach A |

### Selected Approach

**Approach B (Group Card Dashboard)** is selected as the base design. It most directly matches what interviewees said: they want to know their balance at a glance without navigating. The top 4 standout ideas from Approaches A, C, and D are folded in:
- Total owed pinned at top (from A)
- Inline expense composer replacing modal form (from D)
- Settle button on balance row inside group (from C)
- Activity feed within each group (from A)

---

## 7. Wireframe Storyboard

The wireframe storyboard shows the complete user journey for the primary scenario: **a new user joins a group and logs an expense.**

---

### Screen 1 — Home / Dashboard

```
┌──────────────────────────────────┐
│  SplitEase            [+ Group]  │
│  ────────────────────────────── │
│  Good morning, Arjun             │
│                                  │
│  ┌────────────────────────────┐  │
│  │  Total you owe             │  │
│  │  ₹ 3 2 0                   │  │
│  │  across 2 groups           │  │
│  └────────────────────────────┘  │
│                                  │
│  YOUR GROUPS                     │
│  ┌────────────────────────────┐  │
│  │ 🏠  Flat B-204             │  │
│  │     4 members              │  │
│  │     You owe ₹240      [→]  │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ ✈️  Goa Trip               │  │
│  │     3 members              │  │
│  │     You owe ₹80       [→]  │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ 🍕  Lunch Crew             │  │
│  │     6 members              │  │
│  │     Settled ✓              │  │
│  └────────────────────────────┘  │
│                                  │
│  [Home]  [Activity]  [Profile]   │
└──────────────────────────────────┘
```

---

### Screen 2 — Group Detail

*(User taps "Flat B-204")*

```
┌──────────────────────────────────┐
│  ←  Flat B-204           [⚙️]   │
│  ────────────────────────────── │
│                                  │
│  BALANCES                        │
│  ┌────────────────────────────┐  │
│  │  Rahul  owes you   ₹140    │  │
│  │  Karan  owes you    ₹60    │  │
│  │  You    owe Priya  ₹240   │  │
│  │                    [Settle]│  │
│  └────────────────────────────┘  │
│                                  │
│  SIMPLIFIED DEBTS                │
│  ┌────────────────────────────┐  │
│  │  Pay Priya ₹40             │  │
│  │  (clears all debts)        │  │
│  └────────────────────────────┘  │
│                                  │
│  RECENT EXPENSES                 │
│  Groceries        ₹480     2d ↓  │
│  Electricity      ₹360     1w ↓  │
│  Internet         ₹180     2w ↓  │
│                                  │
│  ┌────────────────────────────┐  │
│  │  + Add expense             │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

---

### Screen 3 — Add Expense (Inline Composer, expanded)

*(User taps "+ Add expense")*

```
┌──────────────────────────────────┐
│  ←  Flat B-204           [⚙️]   │
│  ────────────────────────────── │
│                                  │
│  BALANCES                        │
│  Rahul  owes you   ₹140          │
│  Karan  owes you    ₹60          │
│  You    owe Priya  ₹240          │
│                                  │
│  ════ ADD EXPENSE ════           │
│  ┌────────────────────────────┐  │
│  │  Description               │  │
│  │  [Groceries              ] │  │
│  │                            │  │
│  │  Amount (₹)                │  │
│  │  [  4 8 0                ] │  │
│  │                            │  │
│  │  Paid by                   │  │
│  │  [Arjun (you)          ▼]  │  │
│  │                            │  │
│  │  Split                     │  │
│  │  [● Equal  ○ Exact  ○ %]   │  │
│  │                            │  │
│  │  Split equally among:      │  │
│  │  [✓] Arjun  [✓] Rahul      │  │
│  │  [✓] Karan  [✓] Priya      │  │
│  │                            │  │
│  │  Each pays: ₹120           │  │
│  │                            │  │
│  │  [Cancel]    [Add Expense] │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

---

### Screen 4 — Expense Added Confirmation

```
┌──────────────────────────────────┐
│  ←  Flat B-204           [⚙️]   │
│  ────────────────────────────── │
│                                  │
│      ┌────────────────────┐      │
│      │   ✅               │      │
│      │  Expense added!    │      │
│      │                    │      │
│      │  Groceries  ₹480   │      │
│      │  Split equally     │      │
│      │  4 people → ₹120   │      │
│      │  each              │      │
│      │                    │      │
│      │  3 members will    │      │
│      │  be notified.      │      │
│      │                    │      │
│      │      [Done]        │      │
│      └────────────────────┘      │
│                                  │
└──────────────────────────────────┘
```

---

### Screen 5 — Settle Up Flow

*(User taps "Settle" next to "You owe Priya ₹240")*

```
┌──────────────────────────────────┐
│  ←  Settle with Priya            │
│  ────────────────────────────── │
│                                  │
│  You owe Priya  ₹ 2 4 0          │
│  (across 3 expenses)             │
│                                  │
│  Amount to settle                │
│  ┌────────────────────────────┐  │
│  │  ₹  [  2 4 0            ]  │  │
│  │     [Full amount ✓]        │  │
│  └────────────────────────────┘  │
│                                  │
│  ┌────────────────────────────┐  │
│  │  Note (optional)           │  │
│  │  [Paying via UPI         ] │  │
│  └────────────────────────────┘  │
│                                  │
│  After this settlement:          │
│  You will owe Priya: ₹0 ✓        │
│                                  │
│  [Cancel]       [Mark as Settled]│
│                                  │
└──────────────────────────────────┘
```

---

### Screen 6 — Push Notification (Priya's device)

```
┌──────────────────────────────────┐
│  ┌──────────────────────────┐    │
│  │  SplitEase               │    │
│  │  ─────────────────────── │    │
│  │  💸 Arjun added an       │    │
│  │  expense in Flat B-204   │    │
│  │                          │    │
│  │  Groceries ₹480          │    │
│  │  Your share: ₹120        │    │
│  │                          │    │
│  │  [View]     [Dismiss]    │    │
│  └──────────────────────────┘    │
└──────────────────────────────────┘
```

---

## 8. Validation — Customer Feedback

I showed the wireframe storyboard to 5 customers over 2 days. Each session was 15–20 minutes: I walked them through the screens and asked them to think aloud.

---

#### Validation Session 1 — Rahul Nair *(same as interview 1)*

**Task given:** "Imagine you just paid for groceries. Add the expense."

**Observations:**
- Rahul navigated to the group page without hesitation.
- He tapped "+ Add expense" immediately and filled the form in about 20 seconds.
- He paused at "Split: Equal / Exact / %". He said: "I don't know what Exact or Percentage means here."
- He found the confirmation screen reassuring: "I like that it says 3 members will be notified. That means I don't have to message them."

**Feedback:**
- ✅ "Simpler than Splitwise, I'd actually use this."
- ⚠️ "Exact and Percentage split options need a tooltip or example."
- ⚠️ "The 'Simplified Debts' section — what does 'Pay Priya ₹40 (clears all debts)' mean? Explain how."

---

#### Validation Session 2 — Ananya Krishnan *(same as interview 2)*

**Task given:** "You're in the middle of a trip. Add a restaurant bill of ₹1,200 split between 3 friends."

**Observations:**
- Ananya was very fast. She completed the task in about 15 seconds.
- She specifically commented on the "Each pays: ₹400" live calculation. "That's exactly what I wanted. In Splitwise you add it and have to go back and check."
- She tried tapping the group card from the home screen expecting to see a full balance summary — found it, approved.

**Feedback:**
- ✅ "The live '₹400 each' preview while I'm typing the amount is perfect."
- ⚠️ "I want to see the expense date. What if I'm adding it the day after?"
- ⚠️ "Where do I add someone to the group? I couldn't find it easily."

---

#### Validation Session 3 — Karan Bose *(same as interview 3)*

**Task given:** "Check what you owe in the Flat group and settle it."

**Observations:**
- Karan navigated to the group page and looked at the Balances section first.
- He then noticed the "Simplified Debts" section and seemed confused. He said: "How is it ₹40 when I owe ₹240? I feel like something is wrong."
- He found the "Settle" button quickly once he understood.

**Feedback:**
- ✅ "Balance per person is clear. Good."
- ⚠️ "Simplified Debt section needs a better explanation. Maybe 'After offsetting what Rahul owes you, you only need to pay ₹40.'"
- ⚠️ "I want to see a list of which expenses make up my ₹240 debt. Let me tap into it."

---

#### Validation Session 4 — Divya Menon *(same as interview 4)*

**Task given:** "Just explore the app. What would you do first?"

**Observations:**
- Divya went to the home screen and immediately focused on the "Total you owe ₹320" card.
- She said: "This is good. I know exactly where I stand."
- She spent time on the group cards. She tried long-pressing one, expecting options. Nothing happened.
- She found the add-expense form clean and not overwhelming.

**Feedback:**
- ✅ "Not scary like Splitwise. I would actually open this and use it."
- ✅ "The confirmation screen telling me 'members will be notified' is great — that's my biggest pain point solved."
- ⚠️ "Long press on group card should show quick options (like 'Add expense directly')."
- ⚠️ "I want a dark mode option. Most apps I use are dark."

---

#### Validation Session 5 — Siddharth Rao *(same as interview 5)*

**Task given:** "You've been on a trip. Three people owe you money. Walk me through settling it."

**Observations:**
- Siddharth was the most critical tester. He is an experienced Splitwise user.
- He appreciated the simplified debt feature immediately. "This is what I've always wanted. In Splitwise I have to settle 4 people individually."
- He wanted to see the "how" behind the simplification — an explanation or breakdown.
- He noticed the absence of a date field on expenses and said: "That's a blocker for trips where I log 3 days of expenses on the last day."

**Feedback:**
- ✅ "Simplified debt is genuinely better than Splitwise's approach. This is the killer feature."
- ✅ "The group balance view is cleaner than anything I've used."
- ⚠️ "No date field on expense entry is a blocker. Needs to be added."
- ⚠️ "I want to filter expenses by date range. Trips accumulate a lot."

---

### Validation Summary

| Issue | Raised by | Priority |
|---|---|---|
| Date field missing from Add Expense | Ananya, Siddharth | **Critical** |
| Simplified Debt explanation unclear | Rahul, Karan | **High** |
| Where to add group members not obvious | Ananya | **High** |
| Debt breakdown (which expenses make up my ₹240) | Karan | Medium |
| Long press on group card for quick actions | Divya | Low |
| Dark mode | Divya | Low |
| Expense date filter | Siddharth | Low |
| Tooltip for Exact / Percentage split | Rahul | Low |

---

## 9. Iteration — Revised Wireframes

Based on validation feedback, the following changes were made:

### Change 1 — Date field added to Add Expense (Critical)

Added an optional date picker to the expense composer, defaulting to today but easily changeable.

```
BEFORE:                              AFTER:
│  Description           │           │  Description           │
│  [Groceries          ] │           │  [Groceries          ] │
│                        │           │                        │
│  Amount (₹)            │           │  Amount (₹)            │
│  [  4 8 0            ] │           │  [  4 8 0            ] │
                                     │                        │
                                     │  Date                  │
                                     │  [Today, 6 Jun ▼]      │
```

### Change 2 — Simplified Debt explanation (High)

Replaced "Pay Priya ₹40 (clears all debts)" with an expandable explanation.

```
BEFORE:                              AFTER:
  SIMPLIFIED DEBTS                    SIMPLIFIED DEBTS  [?]
  ┌──────────────────────┐            ┌──────────────────────────────┐
  │  Pay Priya ₹40       │            │  Pay Priya ₹40               │
  │  (clears all debts)  │            │  This clears all your debts  │
  └──────────────────────┘            │  because Rahul & Karan owe   │
                                      │  you ₹160, which offsets     │
                                      │  ₹200 of your ₹240 to Priya. │
                                      └──────────────────────────────┘
```

### Change 3 — Group members accessible from group header (High)

Added a visible "Members" pill on the group detail screen.

```
BEFORE:                              AFTER:
│  ←  Flat B-204   [⚙️] │           │  ←  Flat B-204      [⚙️]     │
│  ─────────────────── │            │  Arjun · Rahul · +2  [Manage] │
│                      │            │  ──────────────────────────── │
```

### Change 4 — Expense breakdown link on balance row (Medium)

Added a "3 expenses →" link under each balance so users can see what makes up the amount.

```
BEFORE:                              AFTER:
│  You  owe Priya ₹240  │            │  You  owe Priya  ₹240         │
│               [Settle]│            │  3 expenses →     [Settle]    │
```

### Final Revised Group Detail Screen

```
┌──────────────────────────────────┐
│  ←  Flat B-204           [⚙️]   │
│  Arjun · Rahul · +2   [Manage]  │
│  ────────────────────────────── │
│                                  │
│  BALANCES                        │
│  ┌────────────────────────────┐  │
│  │  Rahul  owes you  ₹140     │  │
│  │  2 expenses →              │  │
│  │  Karan  owes you   ₹60     │  │
│  │  1 expense →               │  │
│  │  ─────────────────────── │  │
│  │  You    owe Priya ₹240    │  │
│  │  3 expenses →   [Settle]   │  │
│  └────────────────────────────┘  │
│                                  │
│  SIMPLIFIED DEBTS  [?]           │
│  ┌────────────────────────────┐  │
│  │  Pay Priya ₹40             │  │
│  │  Rahul & Karan owe you     │  │
│  │  ₹200, which offsets most  │  │
│  │  of your debt to Priya.    │  │
│  └────────────────────────────┘  │
│                                  │
│  RECENT EXPENSES                 │
│  Groceries      ₹480  6 Jun  ↓   │
│  Electricity    ₹360  30 May ↓   │
│                                  │
│  ┌────────────────────────────┐  │
│  │  + Add expense             │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

---

## Appendix A — Work Summary

All work — interviews, ideation, sketching, wireframing, validation, and documentation — was completed individually by Karan Banjade (2023SL70034).

| Activity | Description |
|---|---|
| Customer interviews | Conducted all 5 interviews (Rahul, Ananya, Karan B., Divya, Siddharth) |
| Sketches | Drew all 4 design approaches independently |
| Wireframe storyboard | Designed all 6 screens |
| Validation sessions | Conducted all 5 validation sessions |
| Documentation | Full report authored by Karan Banjade |

---

## Appendix B — Interview Schedule

| Interview | Interviewee | Date | Duration | Interviewer |
|---|---|---|---|---|
| 1 | Rahul Nair | Week 3, Day 1 | 25 min | Karan Banjade |
| 2 | Ananya Krishnan | Week 3, Day 2 | 20 min | Karan Banjade |
| 3 | Karan Bose | Week 3, Day 3 | 30 min | Karan Banjade |
| 4 | Divya Menon | Week 3, Day 4 | 20 min | Karan Banjade |
| 5 | Siddharth Rao | Week 3, Day 5 | 35 min | Karan Banjade |
| V1 (Validation) | Rahul Nair | Week 8, Day 1 | 20 min | Karan Banjade |
| V2 | Ananya Krishnan | Week 8, Day 1 | 15 min | Karan Banjade |
| V3 | Karan Bose | Week 8, Day 2 | 20 min | Karan Banjade |
| V4 | Divya Menon | Week 8, Day 2 | 15 min | Karan Banjade |
| V5 | Siddharth Rao | Week 8, Day 3 | 25 min | Karan Banjade |

---

*End of SPM Assignment Report*
*SplitEase — AY 2025–26*
