"""FastAPI application: chat endpoint + admin guardrail views.

Run locally:
    PYTHONPATH=src uvicorn secure_rag.app:app --reload --port 8000

Admin endpoints require the header ``X-Role: admin`` — in a real deployment
this would be an authenticated admin identity from the IdP; the header check
here exists so the *shape* of the control (guardrail telemetry is itself
sensitive) is visible and tested.
"""

from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException

from .schemas import ChatRequest, ChatResponse, GuardrailEventOut
from .service import ChatService

app = FastAPI(
    title="Secure RAG Chatbot with Guardrails",
    description=(
        "Enterprise RAG with ACL-enforced retrieval, prompt-injection and PII "
        "screening, groundedness verification, and a full audit trail."
    ),
    version="1.0.0",
)

service = ChatService()


def _require_admin(x_role: str | None) -> None:
    if x_role != "admin":
        raise HTTPException(status_code=403, detail="admin role required")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "chunks_indexed": len(service.index)}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    return service.chat(req)


@app.get("/admin/guardrail-events", response_model=list[GuardrailEventOut])
def guardrail_events(
    trace_id: str | None = None,
    x_role: str | None = Header(default=None),
) -> list[GuardrailEventOut]:
    _require_admin(x_role)
    return [
        GuardrailEventOut(**e.to_dict()) for e in service.audit.events(trace_id)
    ]


@app.get("/admin/stats")
def guardrail_stats(x_role: str | None = Header(default=None)) -> dict:
    _require_admin(x_role)
    return service.audit.stats()


@app.get("/admin/documents")
def documents(x_role: str | None = Header(default=None)) -> list[dict]:
    """Index inventory: metadata only — never chunk text."""
    _require_admin(x_role)
    seen: dict[str, dict] = {}
    for chunk in service.index.chunks:
        entry = seen.setdefault(
            chunk.doc_id,
            {
                "doc_id": chunk.doc_id,
                "title": chunk.title,
                "department": chunk.department,
                "classification": chunk.classification,
                "allowed_roles": [r.value for r in chunk.allowed_roles],
                "chunks": 0,
            },
        )
        entry["chunks"] += 1
    return list(seen.values())
