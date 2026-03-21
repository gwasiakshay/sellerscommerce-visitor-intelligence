# SellersCommerce — Visitor Intelligence & Automated Outreach System

**Founder's Office Take-Home Assignment · March 2026**  
**Designed & Built by:** Akshay Gwasikoti · [ak.gwasi@gmail.com](mailto:ak.gwasi@gmail.com) · [github.com/gwasiakshay](https://github.com/gwasiakshay)

---

## The Problem

Most B2B SaaS companies lose 95%+ of their pricing page visitors without ever knowing who they were.

SellersCommerce's pricing page attracts high-intent buyers — but anonymous traffic means no follow-up, no context, and no meeting booked. A visitor who spent 4 minutes comparing the Growth and Enterprise plans is a warm lead. Without a system, they disappear.

**This system turns anonymous pricing page intent into booked meetings — automatically, without looking spammy, and without a human in the loop until a meeting is confirmed.**

---

## How It Works

```
Visitor lands on pricing page
        ↓
High-intent behaviour detected (named trigger fires)
        ↓
Corporate IP → company identity resolved (Clearbit Reveal)
        ↓
Decision-maker contact found (Apollo.io)
        ↓
CRM guardrails checked (HubSpot) — existing customer? Recent outreach? Opted out?
        ↓
Tier-based routing: Enterprise / Mid-Market / SME
        ↓
LLM generates personalised email (FastAPI microservice + OpenRouter)
        ↓
Email sent via SendGrid with pre-tagged Calendly link
        ↓
All activity logged (Google Sheets audit log)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Pricing Page (JS Pixel via GTM)             │
│         Behaviour tracking → Webhook fires to n8n            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                        n8n (Orchestration)                    │
│                                                               │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────────┐ │
│  │   Trigger   │   │  Enrichment  │   │  CRM Guardrails   │ │
│  │   Filter    │──▶│  Pipeline    │──▶│  (HubSpot check)  │ │
│  │  (IF nodes) │   │Clearbit →    │   │  Suppression      │ │
│  └─────────────┘   │Apollo →      │   └────────┬──────────┘ │
│                    │Assemble      │            │             │
│                    └──────────────┘            ▼             │
│                    ┌───────────────────────────────────────┐ │
│                    │         Tier-Based Router              │ │
│                    │  Enterprise / Mid-Market / SME         │ │
│                    └──────┬──────────────┬─────────────────┘ │
└───────────────────────────┼──────────────┼───────────────────┘
               Slack Alert  │              │ FastAPI Call
          (sales rep)       │              │
             ┌──────────────▼──┐    ┌──────▼─────────────────┐
             │  Enterprise     │    │  FastAPI + OpenRouter   │
             │  Human Handoff  │    │  Personalisation Agent  │
             └─────────────────┘    └──────────┬──────────────┘
                                               │
                                    ┌──────────▼──────────────┐
                                    │  SendGrid Email Delivery │
                                    └──────────┬──────────────┘
                                               │
                                    ┌──────────▼──────────────┐
                                    │  Google Sheets Audit Log │
                                    └─────────────────────────┘
```

---

## Tech Stack

| Layer | Tool | Why |
|-------|------|-----|
| Visitor Tracking | Custom JS Pixel via GTM | Fires structured JSON events on named trigger conditions — no site code changes needed |
| Orchestration | **n8n** | All logic in one inspectable, debuggable workflow — no code deploys to change behaviour |
| IP Resolution | **Clearbit Reveal** | Corporate IP → company name, industry, size. First identity signal before any form fill |
| Contact Discovery | **Apollo.io** | Company domain → ICP-matching decision-maker with verified email |
| Full Enrichment | **Clearbit Enrichment** | Email → full firmographic profile, title seniority, tech stack signals |
| CRM & Suppression | **HubSpot** | Existing customer check, 30-day suppression, opt-out compliance, lifecycle tracking |
| AI Personalisation | **FastAPI + OpenRouter LLM** | Structured context → personalised subject line + email opening, cached per profile hash |
| Email Delivery | **SendGrid** | Deliverability controls, daily send cap, domain warm-up, open/click webhooks |
| Audit & Logging | **Google Sheets → PostgreSQL** | Append-only execution log. One-node swap to Postgres at 10K+ monthly visits |
| Error Alerting | **Slack Webhook** | Ops channel alert on any API failure or execution error |

---

## The 5 Named High-Intent Triggers

Each trigger has a name — because naming a signal forces precision about what it actually means.

| Trigger | Signal | Threshold |
|---------|--------|-----------|
| **The Comparison Deep-Dive** | Extended time on pricing tier comparison section | >45s on comparison AND scroll ≥60% |
| **The Return Intensity** | Same corporate IP returns to pricing page | visit_count ≥2 within 48 hours |
| **The ROI Calculator Interaction** | Any input event on calculator elements | Fires immediately on interaction |
| **The Competitive Scroll** | Dwell on SellersCommerce vs. Competitors section | Scroll ≥75% AND dwell ≥20s |
| **The Exit Recapture** | Exit intent after significant engagement | Exit intent AND time_on_page ≥30s AND scroll ≥50% |

**What does NOT trigger the workflow:**
- Internal traffic (IP exclusion list)
- Bot/crawler traffic (user-agent filter at pixel level)
- Existing customers (HubSpot guardrail — checked before any enrichment)
- Contacts outreached in last 30 days (global suppression)
- Mobile visitors under 30 seconds (too low signal strength)

---

## The Three-Tier Routing

| Tier | Condition | Action |
|------|-----------|--------|
| **Enterprise** | >200 employees OR C-suite/VP title | Slack alert to sales rep — no automated email |
| **Mid-Market** | 50–200 employees AND ICP title matched | AI-personalised email sent immediately |
| **SME** | <50 employees | Logged only — never emailed |

**Why Enterprise gets Slack, not email:** An automated email to a VP at a 500-person company signals low effort. A personal follow-up from a sales rep, armed with the full enriched profile, converts at a higher rate. The workflow's job for Enterprise is intelligence delivery, not outreach.

---

## The AI Personalisation Layer

The FastAPI microservice receives the enriched visitor object and calls an LLM via OpenRouter to generate:
- A personalised subject line (max 60 chars, no spam words)
- A 2-3 sentence opening paragraph referencing company + relevant feature
- A soft CTA with pre-tagged Calendly link

**Feature mapping logic** maps visitor industry to the most relevant SellersCommerce feature:

| Industry | Hero Feature Referenced |
|----------|------------------------|
| Industrial Distribution / Manufacturing | Dealer Portal management |
| Fashion / Apparel | Variant management and bulk catalogue upload |
| Electronics | Bundle pricing and warranty SKU management |
| Food / Grocery | Expiry tracking and reorder automation |
| E-commerce Technology | Headless commerce and API-first architecture |
| Global / Multi-region | Multi-storefront management from a single backend |

**Fallback design:** If the LLM fails or returns invalid JSON, the service returns `fallback_used: true` and n8n switches to a static personalised template. Email always sends — personalisation failure never blocks delivery.

---

## Repo Structure

```
sellerscommerce-visitor-intelligence/
│
├── README.md                              # This document
│
├── fastapi/
│   ├── main.py                            # FastAPI personalisation microservice
│   ├── prompt_template.py                 # LLM prompt builder + feature mapping logic
│   └── requirements.txt                   # Python dependencies
│
├── simulator/
│   └── mock_visitor.py                    # Simulates JS pixel events for 5 personas
│
├── n8n/
│   └── workflow_schema.json               # Full n8n workflow structure (credentials redacted)
│
├── data/
│   ├── sample_enriched_visitors.json      # 5 visitor profiles post-enrichment
│   └── sample_email_outputs.json          # Example personalised email outputs
│
└── docs/
    ├── SellersCommerce_Workflow_v2_Akshay.docx   # Full 9-section architecture document
    └── From-Anonymous-Traffic-to-Booked-Meetings.pptx  # Visual presentation
```

---

## Running Locally

### FastAPI Personalisation Service

```bash
cd fastapi
pip install -r requirements.txt

# Add your OpenRouter API key
export OPENROUTER_API_KEY=your_key_here

# Start the service
uvicorn main:app --reload --port 8000

# API docs available at:
# http://localhost:8000/docs
```

### Test the Personalisation Endpoint

```bash
curl -X POST http://localhost:8000/personalise \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Sarah",
    "company_name": "GlobalParts Inc.",
    "job_title": "VP Operations",
    "industry": "Industrial Distribution",
    "pricing_tier_clicked": "Enterprise",
    "trigger_type": "The Comparison Deep-Dive",
    "visit_count": 2,
    "visit_type": "return",
    "company_size_band": "Enterprise",
    "hero_feature": "Dealer Portal management",
    "calendly_link": "https://calendly.com/sellerscommerce/demo"
  }'
```

### Run the Visitor Simulator

```bash
cd simulator

# Simulate one random visitor
python mock_visitor.py

# Simulate a specific persona
python mock_visitor.py --persona enterprise_distributor

# Fire all 5 personas
python mock_visitor.py --all

# Show enriched visitor objects (post Clearbit + Apollo)
python mock_visitor.py --enriched

# Send to real n8n webhook
python mock_visitor.py --all --endpoint https://your-n8n-url/webhook/sellerscommerce-pricing-intent
```

---

## Error Handling

Every external API is a failure point. The design principle: **fail safe, not silent.**

| Failure Point | Recovery | Escalation |
|---------------|----------|------------|
| Pixel payload malformed | Reject + log to error sheet | Slack alert if >5/hour |
| Clearbit confidence <80% | EXIT → human review queue | Log for manual research |
| Clearbit rate limit (429) | Retry 3x with exponential backoff | Slack alert after 3rd fail |
| Apollo no ICP contact found | EXIT → ICP miss sheet | Review filters weekly |
| HubSpot upsert failure | Retry 3x → manual import queue | Slack alert to ops |
| LLM returns invalid JSON | Return fallback_used=true, static template | Log LLM failure rate |
| SendGrid bounce | Mark invalid in HubSpot, remove from sends | Auto-flag for manual review |
| n8n execution crash | Retry once automatically | Slack alert with execution ID |

---

## Anti-Spam Safeguards

- **30-day global suppression** — No domain receives more than one automated outreach per 30 days
- **SME hard block** — Companies under 50 employees are logged but never emailed
- **Opt-out hard block** — HubSpot opt-out list checked before any enrichment API is called
- **Daily send cap** — Configurable via SendGrid. Overflow queued, not dropped
- **Domain warm-up** — First deployment starts at 50 sends/day, scales 25%/week

---

## What I Would Build Next

1. **Live pixel integration** — Connect JS pixel to real pricing page; calibrate trigger thresholds against actual traffic data
2. **A/B test email templates** — Run subject line variants across same tier; feed open/reply rates back into feature map logic
3. **Reply detection loop** — When contact replies, automatically pause all outreach for that domain and notify sales rep in Slack
4. **Calendly → CRM closed loop** — When meeting booked, auto-create HubSpot deal with full enrichment context attached
5. **Real-time dashboard** — Visitors triggered → enriched → emailed → replied → booked, visible in one view

---

## About This Project

Designed and built as a take-home assignment for the **Founder's Office Associate / AI Prototyper in Residence** role at SellersCommerce (March 2026).

The brief: design an automation workflow that converts pricing page visitors into booked meetings.

Three principles guided every design decision:
1. **Deliverability first** — your sender domain is a business asset. The SME hard block and 30-day suppression exist to protect it.
2. **Personalisation that doesn't feel automated** — the feature mapping logic and LLM layer exist so every email references something specific, not generic.
3. **Fail-safe execution** — a workflow that silently fails is worse than one that never ran. Every API failure has an explicit recovery path.

---

*Akshay Gwasikoti · [ak.gwasi@gmail.com](mailto:ak.gwasi@gmail.com) · [LinkedIn](https://linkedin.com/in/akshay-gwasikoti-1223a01a9) · [GitHub](https://github.com/gwasiakshay)*
