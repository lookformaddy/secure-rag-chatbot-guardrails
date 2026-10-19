"""Pydantic schemas shared across the service."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    """User roles used for document-level access control."""

    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR = "hr"
    FINANCE = "finance"
    ADMIN = "admin"


class Decision(str, Enum):
    ALLOW = "allow"
    ALLOW_WITH_REDACTION = "allow_with_redaction"
    BLOCK = "block"
    REFUSE = "refuse"


class ReasonCode(str, Enum):
    """Stable, machine-readable reason codes attached to every guardrail event."""

    OK = "OK"
    INJECTION_DETECTED = "INJECTION_DETECTED"
    PII_IN_INPUT_REDACTED = "PII_IN_INPUT_REDACTED"
    SENSITIVE_DISCLOSURE_REQUEST = "SENSITIVE_DISCLOSURE_REQUEST"
    NO_ACCESSIBLE_CONTENT = "NO_ACCESSIBLE_CONTENT"
    ACCESS_FILTERED_CHUNKS = "ACCESS_FILTERED_CHUNKS"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    PII_IN_OUTPUT_REDACTED = "PII_IN_OUTPUT_REDACTED"
    UNGROUNDED_ANSWER = "UNGROUNDED_ANSWER"
    ANSWER_OK = "ANSWER_OK"


class Document(BaseModel):
    """A source document plus its access-control metadata."""

    doc_id: str
    title: str
    department: str
    classification: str = Field(
        description="public-internal | internal | confidential | restricted"
    )
    allowed_roles: list[Role]
    text: str


class Chunk(BaseModel):
    """An indexed unit of a document. ACL metadata is copied onto every chunk
    so the retriever can enforce permissions without a second lookup."""

    chunk_id: str
    doc_id: str
    title: str
    department: str
    classification: str
    allowed_roles: list[Role]
    text: str
    embedding: list[float] = Field(default_factory=list, repr=False)


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    role: Role
    message: str = Field(min_length=1, max_length=4000)


class Citation(BaseModel):
    doc_id: str
    title: str
    chunk_id: str


class ChatResponse(BaseModel):
    trace_id: str
    decision: Decision
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    reason_codes: list[ReasonCode] = Field(default_factory=list)


class GuardrailEventOut(BaseModel):
    event_id: str
    trace_id: str
    timestamp: str
    stage: str
    decision: Decision
    reason_code: ReasonCode
    user_id: str
    role: Role
    detail: str
