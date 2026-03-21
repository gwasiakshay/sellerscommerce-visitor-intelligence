"""
SellersCommerce — Visitor Intelligence & Automated Outreach System
FastAPI Personalisation Microservice

Receives an enriched visitor object from n8n.
Calls OpenRouter LLM to generate personalised email copy.
Returns validated subject line + opening paragraph + CTA.
Falls back to static template if LLM fails.

Author: Akshay Gwasikoti
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Optional
import httpx
import json
import re
import os
from datetime import datetime

from prompt_template import build_prompt, STATIC_FALLBACK

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SellersCommerce Personalisation API",
    description="LLM-powered email personalisation microservice for pricing page visitor outreach",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ───────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "anthropic/claude-haiku-4-5")
MAX_RETRIES        = 3

# ── Input Schema ─────────────────────────────────────────────────────────────
class EnrichedVisitor(BaseModel):
    # Identity
    first_name: str
    company_name: str
    job_title: str
    industry: str

    # Behavioural signals
    pricing_tier_clicked: str           # e.g. "Growth", "Pro", "Enterprise"
    trigger_type: str                   # e.g. "The Comparison Deep-Dive"
    visit_count: int = 1
    visit_type: str = "first"           # "first" or "return"

    # Enrichment
    company_size_band: str              # "SME", "Mid-Market", "Enterprise"
    hero_feature: str                   # matched by feature mapping logic

    # Delivery
    calendly_link: str

    # Optional
    linkedin_url: Optional[str] = None

    @validator("visit_type")
    def validate_visit_type(cls, v):
        if v not in ["first", "return"]:
            raise ValueError("visit_type must be 'first' or 'return'")
        return v

    @validator("company_size_band")
    def validate_size_band(cls, v):
        if v not in ["SME", "Mid-Market", "Enterprise"]:
            raise ValueError("company_size_band must be SME, Mid-Market, or Enterprise")
        return v


# ── Output Schema ────────────────────────────────────────────────────────────
class PersonalisedEmail(BaseModel):
    subject_line: str
    opening_paragraph: str
    cta_line: str
    fallback_used: bool = False
    model_used: Optional[str] = None
    generated_at: str


# ── LLM Call ─────────────────────────────────────────────────────────────────
async def call_openrouter(prompt: str) -> dict:
    """
    Calls OpenRouter with the personalisation prompt.
    Returns parsed JSON from LLM response.
    Raises on failure after MAX_RETRIES.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/gwasiakshay/sellerscommerce-visitor-intelligence",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "max_tokens": 500,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a B2B sales assistant for SellersCommerce, an agentic B2B commerce platform. "
                    "You write concise, specific, non-pushy outreach emails to senior decision-makers. "
                    "You MUST respond with valid JSON only — no preamble, no markdown, no extra text."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                raw_text = data["choices"][0]["message"]["content"]

                # Strip markdown fences if present
                clean = re.sub(r"```json|```", "", raw_text).strip()
                return json.loads(clean)

        except (httpx.HTTPStatusError, httpx.TimeoutException, json.JSONDecodeError) as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"LLM call failed after {MAX_RETRIES} attempts: {str(e)}")
            continue


# ── Validation ───────────────────────────────────────────────────────────────
def validate_email_fields(data: dict) -> tuple[bool, str]:
    """
    Validates LLM output fields against guardrails.
    Returns (is_valid, reason_if_invalid).
    """
    subject = data.get("subject_line", "")
    opening = data.get("opening_paragraph", "")
    cta     = data.get("cta_line", "")

    # Subject line guardrails
    if not subject or len(subject) > 60:
        return False, f"Subject line too long or missing ({len(subject)} chars)"

    spam_words = ["free", "guarantee", "guaranteed", "urgent", "act now", "limited time"]
    if any(word in subject.lower() for word in spam_words):
        return False, f"Subject line contains spam trigger word"

    if subject != subject.upper() and subject.isupper():
        return False, "Subject line is ALL CAPS"

    # Opening paragraph guardrails
    if not opening or len(opening.split(".")) > 4:
        return False, "Opening paragraph too long or missing"

    # Must reference company or feature
    # (light check — LLM is prompted to include these)
    if len(opening) < 50:
        return False, "Opening paragraph too short — likely incomplete"

    # CTA guardrails
    if not cta or len(cta) > 200:
        return False, "CTA line missing or too long"

    return True, ""


# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "SellersCommerce Personalisation API",
        "version": "1.0.0"
    }


@app.post("/personalise", response_model=PersonalisedEmail)
async def personalise_email(visitor: EnrichedVisitor):
    """
    Main endpoint. Receives enriched visitor, returns personalised email fields.
    Falls back to static template if LLM fails or returns invalid output.
    """
    fallback_used = False
    model_used    = None

    # Build prompt from visitor context
    prompt = build_prompt(visitor.dict())

    try:
        if not OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY not set — using fallback")

        llm_output = await call_openrouter(prompt)
        is_valid, reason = validate_email_fields(llm_output)

        if not is_valid:
            print(f"[VALIDATION FAIL] {reason} — using fallback")
            raise ValueError(reason)

        model_used = OPENROUTER_MODEL

        return PersonalisedEmail(
            subject_line       = llm_output["subject_line"],
            opening_paragraph  = llm_output["opening_paragraph"],
            cta_line           = llm_output["cta_line"],
            fallback_used      = False,
            model_used         = model_used,
            generated_at       = datetime.utcnow().isoformat()
        )

    except Exception as e:
        print(f"[FALLBACK TRIGGERED] Reason: {str(e)}")
        fallback_used = True
        fallback      = STATIC_FALLBACK(visitor.dict())

        return PersonalisedEmail(
            subject_line       = fallback["subject_line"],
            opening_paragraph  = fallback["opening_paragraph"],
            cta_line           = fallback["cta_line"],
            fallback_used      = True,
            model_used         = None,
            generated_at       = datetime.utcnow().isoformat()
        )


@app.post("/personalise/batch")
async def personalise_batch(visitors: list[EnrichedVisitor]):
    """
    Batch endpoint for processing multiple visitors at once.
    Returns list of personalised emails in same order as input.
    """
    if len(visitors) > 50:
        raise HTTPException(status_code=400, detail="Batch size limit is 50 visitors")

    results = []
    for visitor in visitors:
        result = await personalise_email(visitor)
        results.append({
            "company_name": visitor.company_name,
            "email": result.dict()
        })

    return {"count": len(results), "results": results}
