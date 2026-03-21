"""
SellersCommerce — Mock Visitor Payload Simulator

Simulates what the JS pixel would send to the n8n webhook
when a high-intent pricing page visitor is detected.

Usage:
    python mock_visitor.py                    # fires one random visitor
    python mock_visitor.py --persona power    # fires specific persona
    python mock_visitor.py --all              # fires all 5 personas
    python mock_visitor.py --endpoint <url>   # send to real n8n webhook

Author: Akshay Gwasikoti
"""

import json
import argparse
import random
import time
from datetime import datetime, timezone

try:
    import httpx
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False


# ── Visitor Personas ──────────────────────────────────────────────────────────
# Five realistic B2B visitor profiles covering different
# industries, seniority levels, and intent signals.

PERSONAS = {

    "enterprise_distributor": {
        "description": "VP Operations at large industrial distributor — strong buy signal",
        "payload": {
            "visitor_id":          "vis_001_ent_dist",
            "session_id":          "sess_abc123",
            "timestamp":           None,                   # set at runtime
            "ip_address":          "203.0.113.45",         # mock corporate IP
            "pages_visited":       ["pricing", "features/dealer-portal", "case-studies"],
            "time_on_pricing":     312,                    # seconds
            "scroll_depth":        78,                     # percent
            "trigger_type":        "The Comparison Deep-Dive",
            "pricing_tier_clicked":"Enterprise",
            "visit_count":         2,
            "visit_type":          "return",
            "utm_source":          "google",
            "utm_medium":          "cpc",
            "utm_campaign":        "b2b-commerce-2026",
            "device":              "desktop",
            "user_agent":          "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
    },

    "midmarket_fashion": {
        "description": "Head of E-commerce at mid-size fashion brand — evaluating Growth plan",
        "payload": {
            "visitor_id":          "vis_002_mm_fash",
            "session_id":          "sess_def456",
            "timestamp":           None,
            "ip_address":          "198.51.100.22",
            "pages_visited":       ["pricing", "features/catalogue-management"],
            "time_on_pricing":     187,
            "scroll_depth":        65,
            "trigger_type":        "The ROI Calculator Interaction",
            "pricing_tier_clicked":"Growth",
            "visit_count":         1,
            "visit_type":          "first",
            "utm_source":          "linkedin",
            "utm_medium":          "organic",
            "utm_campaign":        None,
            "device":              "desktop",
            "user_agent":          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        }
    },

    "return_tech_company": {
        "description": "CTO at tech-forward retail company — third visit, high intent",
        "payload": {
            "visitor_id":          "vis_003_ret_tech",
            "session_id":          "sess_ghi789",
            "timestamp":           None,
            "ip_address":          "192.0.2.88",
            "pages_visited":       ["pricing", "features/api", "docs/integration"],
            "time_on_pricing":     445,
            "scroll_depth":        92,
            "trigger_type":        "The Return Intensity",
            "pricing_tier_clicked":"Pro",
            "visit_count":         3,
            "visit_type":          "return",
            "utm_source":          "direct",
            "utm_medium":          None,
            "utm_campaign":        None,
            "device":              "desktop",
            "user_agent":          "Mozilla/5.0 (X11; Linux x86_64)"
        }
    },

    "competitive_scroll": {
        "description": "Director of Operations evaluating SellersCommerce vs competitor",
        "payload": {
            "visitor_id":          "vis_004_comp_scr",
            "session_id":          "sess_jkl012",
            "timestamp":           None,
            "ip_address":          "10.0.0.157",
            "pages_visited":       ["pricing", "compare"],
            "time_on_pricing":     223,
            "scroll_depth":        81,
            "trigger_type":        "The Competitive Scroll",
            "pricing_tier_clicked":"Growth",
            "visit_count":         1,
            "visit_type":          "first",
            "utm_source":          "google",
            "utm_medium":          "organic",
            "utm_campaign":        None,
            "device":              "desktop",
            "user_agent":          "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
    },

    "exit_recapture": {
        "description": "VP Sales about to leave — exit intent triggered",
        "payload": {
            "visitor_id":          "vis_005_exit_rec",
            "session_id":          "sess_mno345",
            "timestamp":           None,
            "ip_address":          "172.16.0.99",
            "pages_visited":       ["pricing"],
            "time_on_pricing":     95,
            "scroll_depth":        52,
            "trigger_type":        "The Exit Recapture",
            "pricing_tier_clicked":"Growth",
            "visit_count":         1,
            "visit_type":          "first",
            "utm_source":          "email",
            "utm_medium":          "newsletter",
            "utm_campaign":        "march-2026-outreach",
            "device":              "desktop",
            "user_agent":          "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
    }
}


# ── Enriched Output Examples ──────────────────────────────────────────────────
# What n8n produces AFTER Clearbit + Apollo enrichment.
# This is what gets passed to the FastAPI personalisation service.

ENRICHED_EXAMPLES = {

    "enterprise_distributor": {
        "first_name":           "Sarah",
        "company_name":         "GlobalParts Inc.",
        "job_title":            "VP Operations",
        "industry":             "Industrial Distribution",
        "company_size_band":    "Enterprise",
        "pricing_tier_clicked": "Enterprise",
        "trigger_type":         "The Comparison Deep-Dive",
        "visit_count":          2,
        "visit_type":           "return",
        "hero_feature":         "Dealer Portal management",
        "calendly_link":        "https://calendly.com/sellerscommerce/demo?utm_source=pricing-workflow&utm_tier=enterprise&utm_visit=return",
        "linkedin_url":         "https://linkedin.com/in/sarah-example"
    },

    "midmarket_fashion": {
        "first_name":           "Rahul",
        "company_name":         "Trendcraft Apparel",
        "job_title":            "Head of E-commerce",
        "industry":             "Fashion & Apparel",
        "company_size_band":    "Mid-Market",
        "pricing_tier_clicked": "Growth",
        "trigger_type":         "The ROI Calculator Interaction",
        "visit_count":          1,
        "visit_type":           "first",
        "hero_feature":         "variant management and bulk catalogue upload",
        "calendly_link":        "https://calendly.com/sellerscommerce/demo?utm_source=pricing-workflow&utm_tier=growth&utm_visit=first",
        "linkedin_url":         None
    },

    "return_tech_company": {
        "first_name":           "Priya",
        "company_name":         "NexCart Technologies",
        "job_title":            "CTO",
        "industry":             "E-commerce Technology",
        "company_size_band":    "Mid-Market",
        "pricing_tier_clicked": "Pro",
        "trigger_type":         "The Return Intensity",
        "visit_count":          3,
        "visit_type":           "return",
        "hero_feature":         "headless commerce and API-first architecture",
        "calendly_link":        "https://calendly.com/sellerscommerce/demo?utm_source=pricing-workflow&utm_tier=pro&utm_visit=return",
        "linkedin_url":         "https://linkedin.com/in/priya-example"
    }
}


# ── Simulator Logic ───────────────────────────────────────────────────────────
def generate_payload(persona_key: str) -> dict:
    """Returns a pixel event payload for the given persona."""
    persona = PERSONAS[persona_key]
    payload = persona["payload"].copy()
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    return payload


def print_payload(persona_key: str, payload: dict):
    """Pretty-prints the simulated pixel event."""
    persona = PERSONAS[persona_key]
    print(f"\n{'='*60}")
    print(f"PERSONA:     {persona_key}")
    print(f"DESCRIPTION: {persona['description']}")
    print(f"TRIGGER:     {payload['trigger_type']}")
    print(f"TIER VIEWED: {payload['pricing_tier_clicked']}")
    print(f"TIME ON PAGE:{payload['time_on_pricing']}s")
    print(f"SCROLL:      {payload['scroll_depth']}%")
    print(f"VISIT COUNT: {payload['visit_count']}")
    print(f"{'='*60}")
    print(json.dumps(payload, indent=2))


def send_to_webhook(payload: dict, endpoint: str):
    """Sends pixel payload to n8n webhook endpoint."""
    if not HTTP_AVAILABLE:
        print("[ERROR] httpx not installed. Run: pip install httpx")
        return

    try:
        response = httpx.post(endpoint, json=payload, timeout=10.0)
        print(f"\n[WEBHOOK] Status: {response.status_code}")
        print(f"[WEBHOOK] Response: {response.text[:200]}")
    except Exception as e:
        print(f"[WEBHOOK ERROR] {str(e)}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="SellersCommerce Mock Visitor Simulator"
    )
    parser.add_argument(
        "--persona",
        choices=list(PERSONAS.keys()),
        help="Specific persona to simulate"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fire all 5 personas sequentially"
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        help="n8n webhook URL to send payload to"
    )
    parser.add_argument(
        "--enriched",
        action="store_true",
        help="Show enriched visitor objects (post Clearbit+Apollo)"
    )

    args = parser.parse_args()

    if args.enriched:
        print("\n── ENRICHED VISITOR OBJECTS (Post Clearbit + Apollo) ──")
        for key, data in ENRICHED_EXAMPLES.items():
            print(f"\n[{key.upper()}]")
            print(json.dumps(data, indent=2))
        return

    if args.all:
        personas_to_run = list(PERSONAS.keys())
    elif args.persona:
        personas_to_run = [args.persona]
    else:
        # Random persona
        personas_to_run = [random.choice(list(PERSONAS.keys()))]

    for persona_key in personas_to_run:
        payload = generate_payload(persona_key)
        print_payload(persona_key, payload)

        if args.endpoint:
            print(f"\n[SENDING TO WEBHOOK] {args.endpoint}")
            send_to_webhook(payload, args.endpoint)
            if len(personas_to_run) > 1:
                time.sleep(1)   # small delay between batch sends

    print(f"\n✓ Simulated {len(personas_to_run)} visitor event(s)")


if __name__ == "__main__":
    main()
