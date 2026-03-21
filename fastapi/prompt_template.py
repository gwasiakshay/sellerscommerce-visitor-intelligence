"""
SellersCommerce — Personalisation Prompt Templates & Feature Mapping

This module contains:
- Feature mapping table: industry → SellersCommerce hero feature
- LLM prompt builder
- Static fallback template (used when LLM fails)
"""

# ── Feature Mapping ───────────────────────────────────────────────────────────
# Maps visitor industry/profile to the most relevant SellersCommerce feature.
# This is injected into the LLM prompt so it references a SPECIFIC product
# feature rather than generic platform capabilities.

FEATURE_MAP = {
    "industrial distribution":    "Dealer Portal management",
    "manufacturing":               "Dealer Portal management",
    "wholesale":                   "Dealer Portal management",
    "fashion":                     "variant management and bulk catalogue upload",
    "apparel":                     "variant management and bulk catalogue upload",
    "retail":                      "unified order management across channels",
    "electronics":                 "bundle pricing and warranty SKU management",
    "technology":                  "headless commerce and API-first architecture",
    "food":                        "expiry tracking and reorder automation",
    "grocery":                     "expiry tracking and reorder automation",
    "health":                      "subscription and replenishment workflows",
    "healthcare":                  "subscription and replenishment workflows",
    "global":                      "multi-storefront management from a single backend",
    "international":               "multi-storefront management from a single backend",
    "ecommerce":                   "CommerceEDGE agentic workflow automation",
    "default":                     "workflow automation and ERP integration"
}


def get_hero_feature(industry: str, hero_feature_override: str = "") -> str:
    """
    Returns the most relevant SellersCommerce feature for a given industry.
    If hero_feature_override is set (from enrichment), use that directly.
    """
    if hero_feature_override and hero_feature_override != "default":
        return hero_feature_override

    industry_lower = industry.lower()
    for key, feature in FEATURE_MAP.items():
        if key in industry_lower:
            return feature

    return FEATURE_MAP["default"]


# ── Prompt Builder ────────────────────────────────────────────────────────────
def build_prompt(visitor: dict) -> str:
    """
    Builds the LLM prompt from the enriched visitor object.
    Returns a string prompt that instructs the LLM to return valid JSON only.
    """

    hero_feature = get_hero_feature(
        visitor.get("industry", ""),
        visitor.get("hero_feature", "")
    )

    visit_context = ""
    if visitor.get("visit_type") == "return" or visitor.get("visit_count", 1) > 1:
        visit_context = (
            f"This is their {visitor.get('visit_count', 2)}nd visit to the pricing page. "
            "Acknowledge this subtly — they've been evaluating carefully."
        )
    else:
        visit_context = "This is their first visit."

    prompt = f"""
You are writing a B2B outreach email for SellersCommerce, an agentic B2B commerce platform 
used by companies like Walgreens and VF Corp to manage complex e-commerce operations.

VISITOR CONTEXT:
- Name: {visitor.get('first_name', 'there')}
- Company: {visitor.get('company_name', 'their company')}
- Title: {visitor.get('job_title', 'decision-maker')}
- Industry: {visitor.get('industry', 'e-commerce')}
- Pricing plan they viewed: {visitor.get('pricing_tier_clicked', 'Growth')}
- Trigger: {visitor.get('trigger_type', 'pricing page visit')}
- Visit context: {visit_context}
- Most relevant SellersCommerce feature for their business: {hero_feature}
- Meeting link: {visitor.get('calendly_link', 'https://calendly.com/sellerscommerce')}

RULES:
1. Subject line: max 60 characters, no spam words (free/guarantee/urgent), no ALL CAPS, 
   no exclamation marks. Must feel personal, not promotional.
2. Opening paragraph: exactly 2-3 sentences. Must reference the company name OR the 
   hero feature. Must sound like one person who researched their business — not a template.
3. CTA line: exactly 1 sentence. Soft ask for a 20-minute call. Include the calendly link.
4. Never fabricate facts. Only use what is provided above.
5. Tone: confident, specific, non-pushy. Like a peer, not a salesperson.

RESPOND WITH VALID JSON ONLY — no preamble, no markdown, no extra text:
{{
  "subject_line": "...",
  "opening_paragraph": "...",
  "cta_line": "..."
}}
"""
    return prompt.strip()


# ── Static Fallback ───────────────────────────────────────────────────────────
def STATIC_FALLBACK(visitor: dict) -> dict:
    """
    Returns a static but personalised email template.
    Used when LLM fails or returns invalid output.
    Dynamic fields are injected from visitor object.
    Intentionally conservative — safe to send without LLM review.
    """

    first_name    = visitor.get("first_name", "there")
    company_name  = visitor.get("company_name", "your company")
    tier          = visitor.get("pricing_tier_clicked", "Growth")
    hero_feature  = get_hero_feature(
                        visitor.get("industry", ""),
                        visitor.get("hero_feature", "")
                    )
    calendly_link = visitor.get("calendly_link", "https://calendly.com/sellerscommerce")
    visit_type    = visitor.get("visit_type", "first")

    if visit_type == "return":
        subject = f"You came back to our {tier} plan, {first_name}"
        opening = (
            f"I noticed {company_name} has been evaluating our {tier} plan — "
            f"and came back for a second look. That usually means the {hero_feature} "
            f"capability is relevant to something you're working through right now."
        )
    else:
        subject = f"{company_name} + SellersCommerce — worth 20 minutes?"
        opening = (
            f"I saw {company_name} was exploring our {tier} plan earlier. "
            f"Based on your industry, the {hero_feature} features tend to be "
            f"where companies like yours find the most immediate value."
        )

    cta = f"Would a 20-minute walkthrough be useful this week? {calendly_link}"

    return {
        "subject_line":      subject[:60],
        "opening_paragraph": opening,
        "cta_line":          cta
    }
