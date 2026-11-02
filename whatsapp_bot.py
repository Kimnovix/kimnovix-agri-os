from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.core import KimnovixAgriOS

app = FastAPI(
    title="Kimnovix Agri-OS WhatsApp Webhook",
    version="1.0.0",
    description="Deterministic edge webhook interface for field WhatsApp queries.",
)

engine = KimnovixAgriOS()


class WhatsAppInboundPayload(BaseModel):
    sender: str = Field(..., min_length=3, max_length=64, description="Sender phone or ID")
    message: str = Field(..., min_length=1, description="Inbound text query")
    lang: str = Field(default="en", pattern="^(en|sw)$", description="Language code (en or sw)")


class WhatsAppOutboundResponse(BaseModel):
    recipient: str
    status: str
    category: str
    reply: str
    timestamp: str


@app.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe for Docker orchestration."""
    return {"status": "ok", "service": "kimnovix-whatsapp-webhook", "mode": engine.mode}


@app.post("/webhook/whatsapp", response_model=WhatsAppOutboundResponse)
def whatsapp_webhook(payload: WhatsAppInboundPayload) -> WhatsAppOutboundResponse:
    """Process incoming WhatsApp message via the deterministic core router.

    ERROR results (e.g. missing weight or compound) are returned as a normal reply
    so the field worker sees what to resend, instead of an HTTP error with no text.
    """
    result = engine.process_query(query=payload.message, lang=payload.lang)

    return WhatsAppOutboundResponse(
        recipient=payload.sender,
        status=result["status"],
        category=result["category"],
        reply=result["response"],
        timestamp=result["timestamp"],
    )
