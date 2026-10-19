"""Audit log for guardrail decisions.

Every stage of the pipeline records an event: trace id, stage, decision,
reason code, user, role — and a human-readable detail that never contains
raw PII or the text of restricted chunks. In production this would ship to
a SIEM; here it is an in-memory store with an optional JSONL sink, exposed
to admins through the API.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from .schemas import Decision, ReasonCode, Role


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class GuardrailEvent:
    stage: str
    decision: Decision
    reason_code: ReasonCode
    user_id: str
    role: Role
    detail: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["decision"] = self.decision.value
        d["reason_code"] = self.reason_code.value
        d["role"] = self.role.value
        return d


class AuditLog:
    def __init__(self, jsonl_path: str | None = None) -> None:
        self._events: list[GuardrailEvent] = []
        self._lock = threading.Lock()
        self._jsonl_path = jsonl_path

    def record(self, event: GuardrailEvent) -> GuardrailEvent:
        with self._lock:
            self._events.append(event)
            if self._jsonl_path:
                with open(self._jsonl_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(event.to_dict()) + "\n")
        return event

    def events(self, trace_id: str | None = None) -> list[GuardrailEvent]:
        with self._lock:
            evts = list(self._events)
        if trace_id:
            evts = [e for e in evts if e.trace_id == trace_id]
        return evts

    def stats(self) -> dict:
        with self._lock:
            evts = list(self._events)
        by_reason: dict[str, int] = {}
        by_decision: dict[str, int] = {}
        for e in evts:
            by_reason[e.reason_code.value] = by_reason.get(e.reason_code.value, 0) + 1
            by_decision[e.decision.value] = by_decision.get(e.decision.value, 0) + 1
        return {
            "total_events": len(evts),
            "by_reason_code": by_reason,
            "by_decision": by_decision,
        }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
