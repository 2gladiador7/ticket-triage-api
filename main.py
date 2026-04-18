import os
import json
from typing import Optional, List

import anthropic
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# App & clients
# ---------------------------------------------------------------------------

app = FastAPI(title="Ticket Triage API", version="1.0.0")
security = HTTPBearer(auto_error=False)
claude = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CATEGORIES = ["billing", "technical", "account", "feature-request", "general"]

SYSTEM_PROMPT = """You are an expert customer-support ticket triage system.

Given a support ticket and a list of allowed categories, return a JSON object
with exactly these fields:

  category      – one of the provided categories (pick the best fit)
  priority      – "low" | "medium" | "high" | "urgent"
  sentiment     – "positive" | "neutral" | "frustrated" | "angry"
  response_type – snake_case label for the response pattern, e.g.
                  "refund_inquiry", "password_reset", "bug_report",
                  "feature_request", "billing_dispute", "account_access"
  summary       – ONE sentence (≤25 words) summarising the core issue

Priority guide:
  urgent  → data loss, security breach, full service outage, legal threats
  high    → major feature broken, revenue impact, multiple users affected
  medium  → single-user issue with workaround, paying-customer request
  low     → cosmetic bugs, minor inconveniences, general questions

Return ONLY the raw JSON object — no markdown fences, no explanation."""

# JSON Schema passed to output_config so the model is constrained to the shape.
TRIAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "category":      {"type": "string"},
        "priority":      {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
        "sentiment":     {"type": "string", "enum": ["positive", "neutral", "frustrated", "angry"]},
        "response_type": {"type": "string"},
        "summary":       {"type": "string"},
    },
    "required": ["category", "priority", "sentiment", "response_type", "summary"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TriageRequest(BaseModel):
    ticket: str
    categories: Optional[List[str]] = None


class TriageResponse(BaseModel):
    category: str
    priority: str
    sentiment: str
    response_type: str
    summary: str

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": "Malformed input", "errors": exc.errors()})

# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def require_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> None:
    api_key = os.environ.get("API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="API_KEY is not configured on the server")
    if credentials is None or credentials.credentials != api_key:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized — provide a valid Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@app.post("/triage", response_model=TriageResponse)
def triage(body: TriageRequest, _: None = Depends(require_api_key)):
    """Classify and prioritise a support ticket using Claude Haiku."""
    categories = body.categories or DEFAULT_CATEGORIES

    user_content = (
        f"Available categories: {', '.join(categories)}\n\n"
        f"Ticket:\n{body.ticket}"
    )

    try:
        response = claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": TRIAGE_SCHEMA,
                }
            },
        )
    except anthropic.APIError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream API error: {exc}")

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise HTTPException(status_code=502, detail="Empty response from upstream")

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Non-JSON response from upstream")

    return TriageResponse(**data)
