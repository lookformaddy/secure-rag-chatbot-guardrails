"""PII detection and redaction.

Regex-based detectors for the PII classes most likely to appear in an
enterprise corpus or be pasted into a chat box. Every detector is named so
audit events can record *what kind* of PII was seen without recording the
PII itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    # US SSN shape, plus the corpus' synthetic employee-ID shape NNNN-NN-NNNN
    ("SSN_OR_ID", re.compile(r"\b\d{3,4}-\d{2}-\d{4}\b")),
    ("PHONE", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
]


@dataclass
class PIIFinding:
    kind: str
    count: int


@dataclass
class PIIResult:
    text: str
    findings: list[PIIFinding] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return bool(self.findings)

    @property
    def kinds(self) -> list[str]:
        return [f.kind for f in self.findings]


def scan_and_redact(text: str) -> PIIResult:
    """Return the text with every PII occurrence replaced by [REDACTED:KIND]."""
    findings: list[PIIFinding] = []
    redacted = text
    for kind, pattern in _PATTERNS:
        redacted, n = pattern.subn(f"[REDACTED:{kind}]", redacted)
        if n:
            findings.append(PIIFinding(kind=kind, count=n))
    return PIIResult(text=redacted, findings=findings)


def contains_pii(text: str) -> bool:
    return any(pattern.search(text) for _, pattern in _PATTERNS)
