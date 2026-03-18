# SellersCommerce — Visitor Intelligence & Automated Outreach System

**Founder's Office Take-Home Assignment · March 2026**  
**Designed by:** Akshay Gwasikoti · [ak.gwasi@gmail.com](mailto:ak.gwasi@gmail.com) · [github.com/gwasiakshay](https://github.com/gwasiakshay)

---

## The Problem

Most B2B SaaS companies lose 95%+ of their pricing page visitors without ever knowing who they were.

SellersCommerce's pricing page attracts high-intent buyers — but anonymous traffic means no follow-up, no context, and no meeting booked. A visitor who spent 4 minutes comparing the Growth and Enterprise plans is a warm lead. Without a system, they disappear.

**This workflow turns anonymous pricing page intent into booked meetings — automatically, and without ever looking spammy.**

---

## What This System Does

```
Visitor lands on pricing page
        ↓
High-intent behaviour detected (time on page, plan hover, return visit)
        ↓
Corporate IP → company identity resolved (Clearbit)
        ↓
Decision-maker contact found (Apollo)
        ↓
CRM guardrails checked (HubSpot) — existing customer? Recent outreach? Opted out?
        ↓
Tier-based routing: Enterprise / Mid-Market / SME
        ↓
LLM generates personalised email (FastAPI microservice)
        ↓
Email sent via SendGrid with pre-tagged Calendly link
        ↓
All activity logged (Google Sheets / PostgreSQL at scale)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Pricing Page (JS Pixel)                  │
│         Behaviour tracking → Webhook fires to n8n            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                        n8n (Orchestration)                    │
│                                                               │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────────┐ │
│  │   Trigger   │   │  Enrichment  │   │  CRM Guardrails   │ │
│  │   Filter    │──▶│  Pipeline    │──▶│  (HubSpot check)  │ │
│  │  (IF nodes) │   │Clearbit→     │   │  Suppression list │ │
│  └─────────────┘   │Apollo→Score  │   └────────┬──────────┘ │
│                    └──────────────┘            │             │
│                                                ▼             │
│                    ┌───────────────────────────────────────┐ │
│                    │         Tier-Based Router              │ │
│                    │  Enterprise / Mid-Market / SME / Exit  │ │
│                    └──────────┬──────────────┬─────────────┘ │
└───────────────────────────────┼──────────────┼───────────────┘
                                │              │
             ┌──────────────────▼──┐    ┌──────▼─────────────┐
             │  FastAPI (LLM Layer) │    │   Audit Log        │
             │  Personalisation    │    │   Google Sheets /  │
             │  Microservice       │    │   PostgreSQL        │
             └──────────┬──────────┘    └────────────────────┘
                        │
             ┌──────────▼──────────┐
             │  SendGrid           │
             │  (Email Delivery)   │
             └─────────────────────┘
```

---

## Tech Stack

| Layer | Tool | Why |
|-------|------|-----|
| Orchestration | **n8n** | All logic in one inspectable, debuggable workflow — no code deploys to change behaviour |
| Identity Resolution | **Clearbit Reveal** | Corporate IP → company name, industry, size |
| Contact Enrichment | **Apollo.io** | Company → decision-maker name, title, email |
| CRM & Suppression | **HubSpot** | Existing customer check, 30-day suppression, opt-out compliance |
| AI Personalisation | **FastAPI + OpenRouter LLM** | Structured context → personalised email copy, cached per profile hash |
| Email Delivery | **SendGrid** | Deliverability controls, daily send cap, domain warm-up |
| Audit & Logging | **Google Sheets → PostgreSQL** | Append-only execution log; one-node swap to Postgres at scale |

---

## Section 1 — Trigger & Behaviour Logic: Defining High Intent

The workflow does **not** fire on every page visit. It activates only when a visitor's behaviour pattern signals genuine purchase evaluation.

### Named High-Intent Triggers

| Trigger Name | Definition |
|---|---|
| **The Evaluator** | 3+ minutes on pricing page in a single session |
| **The Comparer** | Hovered or clicked 2+ pricing plan cards |
| **The Returner** | Second visit to pricing page within 7 days |
| **The Deep Diver** | Pricing page + Feature comparison page in same session |

### What Does NOT Trigger the Workflow

- **Internal traffic** — IP exclusion list maintained as environment variable in n8n
- **Bot/crawler traffic** — user-agent filtering at pixel level, before webhook fires
- **Existing customers** — CRM guardrail check exits the workflow before any action
- **Recent outreach contacts** — global 30-day suppression check
- **Mobile visitors < 30 seconds** — too low signal strength to justify enrichment API cost

> **Design rationale:** Naming each trigger forces precision about what the signal actually means. "3 minutes on pricing" is not the same as "evaluated two plans." Each has a different implication for how the outreach should read.

---

## Section 2 — The B2B Intelligence Pipeline

Anonymous traffic is not a dead end. A corporate IP carries enough signal to identify the company, find the right person inside it, and build a personalisation context — all before the visitor has filled in a single form field.

### Four-Stage Identity & Intelligence Pipeline

```
Stage 1: IP Resolution
  Pixel captures: IP, pages visited, time on page, plan interactions, session data
  Clearbit Reveal: IP → company name, domain, industry, employee count, location
  
Stage 2: Contact Discovery  
  Apollo.io: company domain → decision-maker (VP Sales / Head of Ecommerce / Founder)
  Filters: seniority ≥ Manager, department = Sales/Operations/Product
  
Stage 3: Profile Assembly
  n8n merges: visitor behaviour + company intel + contact details
  Output: structured JSON object passed to LLM layer
  
Stage 4: Tier Classification
  Enterprise: 200+ employees → immediate personalised outreach
  Mid-Market: 50–200 employees → personalised outreach with slight delay
  SME: < 50 employees → logged only, never emailed (protects sender reputation)
```

---

## Section 3 — AI Personalisation Layer

The LLM does not write a generic template. It receives a structured context object and generates copy that references the visitor's specific company, their likely pain point, and the SellersCommerce feature most relevant to their business model.

### FastAPI Personalisation Microservice

```python
# Context object passed to LLM
{
  "company_name": "Acme Distribution Co.",
  "industry": "Industrial Distribution",
  "employee_count": 340,
  "pricing_tier_clicked": "Growth",
  "visit_count": 2,
  "hero_feature": "Multi-warehouse inventory sync",   # matched by feature map logic
  "first_name": "Rajesh",
  "title": "VP Operations"
}
```

### Feature Mapping Logic

The LLM prompt includes a SellersCommerce feature map. Based on the visitor's industry and company profile, the agent selects the most relevant hero feature:

| Industry | Hero Feature |
|---|---|
| Industrial / B2B Distribution | Multi-warehouse inventory sync |
| Fashion / Apparel | Variant management + bulk catalogue upload |
| Electronics | Bundle pricing + warranty SKU management |
| Food & Grocery | Expiry tracking + reorder automation |
| General Retail | Unified order management across channels |

### 3-Layer Personalisation in Every Email

| Layer | What It Does |
|---|---|
| **Template Selection** | Structural format chosen by tier and visit type (first visit vs. return) |
| **Dynamic Field Injection** | `{{company_name}}`, `{{pricing_tier_clicked}}`, `{{hero_feature}}`, `{{industry}}`, `{{visit_count}}`, `{{calendly_link}}` (pre-tagged with UTM source, tier, visit type) |
| **LLM-Generated Copy** | 2–3 sentences of contextual body copy, written to sound like one person who actually researched the business before reaching out |

> **Goal:** The email should not sound automated. It should sound like the one person who actually paid attention to their business before reaching out.

---

## Section 4 — Workflow Logic & Tier-Based Routing

Every branch in n8n is an explicit **IF node** — no implicit assumptions. The CRM guardrail runs before any enrichment API is called to minimise unnecessary cost.

### Full Execution Sequence

```
Webhook received
  → Filter: is this high-intent? (IF node: behaviour score threshold)
    → No → Exit silently
    → Yes → HubSpot guardrail check
              → Existing customer? → Exit
              → Opted out? → Exit (legal hard block)
              → Outreach in last 30 days? → Exit (suppression)
              → Pass → Clearbit enrichment
                         → Company identified?
                           → No → Log as unresolvable, exit
                           → Yes → Apollo contact lookup
                                    → Contact found?
                                      → No → Log, exit
                                      → Yes → Tier classification
                                               → SME (<50 emp) → Log only
                                               → Mid-Market → FastAPI → SendGrid (30min delay)
                                               → Enterprise → FastAPI → SendGrid (immediate)
                                               → All → Audit log append
```

---

## Section 5 — Error Handling & Scalability

This workflow touches **seven external APIs**. Each is a failure point. The design principle: **fail safe, not silent.**

### API Failure Handling

| API | Failure Mode | Handling |
|---|---|---|
| Clearbit | Rate limit / no match | Retry ×2 with backoff; log as unresolvable on final fail |
| Apollo | Rate limit / no contact | 5-second delay node between calls; queue at high volume |
| HubSpot | Timeout | Retry ×3; exit workflow if unavailable (never skip suppression check) |
| FastAPI / LLM | Timeout / hallucination | Deterministic fallback template used; never sends blank email |
| SendGrid | Bounce / block | Webhook updates HubSpot contact status; suppresses future sends |
| Google Sheets | Write failure | n8n error node fires Slack alert; execution data buffered in memory |

### Anti-Spam & Domain Reputation Safeguards

- **30-day global suppression** — No domain receives more than one automated outreach per 30 days. Enforced as a HubSpot contact property, checked before any enrichment API is called.
- **SME hard block** — Companies below 50 employees are logged but never emailed.
- **Daily send cap** — Configurable maximum daily sends via SendGrid. Overflow queued, not dropped.
- **Domain warm-up sequence** — On first deployment, daily sends start at 50 and scale by 25% per week to prevent blacklisting.
- **Unsubscribe hard block** — HubSpot opt-out list checked before any enrichment is called. This is a legal requirement. It is never overridden.

### Scaling from 50 to 50,000 Visitors/Month

| Component | Scaling Approach |
|---|---|
| n8n | Each webhook runs in an independent worker; n8n Cloud scales horizontally |
| Clearbit | Enrichment results cached as HubSpot properties — same domain is never re-enriched |
| Apollo | 5-second delay between calls; queue depth monitored via Slack |
| LLM | FastAPI caches output per visitor profile hash for 7 days — reduces OpenRouter cost at scale |
| Audit Log | Google Sheets → one-node swap to PostgreSQL at 10K+ monthly visits |

---

## Repo Structure

```
sellerscommerce-visitor-intelligence/
│
├── README.md                          # This document
├── docs/
│   ├── workflow-design.md             # Full section-by-section design spec
│   └── presentation.pdf              # Slide deck: From Anonymous Traffic to Booked Meetings
├── n8n/
│   └── workflow-schema.json          # n8n workflow export (structural — API keys redacted)
└── fastapi/
    └── personalisation-prompt.md     # LLM prompt template + feature mapping logic
```

---

## What I Would Build Next (With Access to SellersCommerce Stack)

1. **Live pixel integration** — Connect JS pixel to real pricing page; test trigger thresholds against actual traffic data
2. **A/B test email templates** — Run Subject Line A vs. B across the same tier; feed open/reply rates back into feature map logic
3. **Reply detection loop** — If contact replies, automatically pause all outreach for that domain and notify the sales rep in Slack
4. **Calendly → CRM closed loop** — When a meeting is booked, auto-create a deal in HubSpot with full enrichment context attached
5. **Dashboard** — Real-time view of pipeline: visitors triggered → enriched → emailed → replied → booked

---

## About This Project

This system was designed as a take-home assignment for the **Founder's Office Associate** role at SellersCommerce (March 2026). The brief: design an automation that converts pricing page visitors into booked meetings.

The design prioritises three things above all else: **deliverability** (your domain reputation is a business asset), **personalisation that doesn't feel automated**, and **fail-safe execution** — because a workflow that silently fails is worse than one that never ran.

---

*Akshay Gwasikoti · [ak.gwasi@gmail.com](mailto:ak.gwasi@gmail.com) · [LinkedIn](https://linkedin.com/in/akshay-gwasikoti-1223a01a9) · [GitHub](https://github.com/gwasiakshay)*
