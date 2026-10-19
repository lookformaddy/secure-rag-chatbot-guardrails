"""Output screening: the last guardrail before an answer reaches the user.

Two checks:
1. Groundedness — every sentence of the answer must be supported by the
   retrieved chunks (content-token overlap above a threshold). Unsupported
   sentences are dropped; if nothing supported remains, the answer is
   refused rather than sent. This is the anti-hallucination control.
2. PII leakage — even when a role is allowed to *retrieve* a document that
   contains personal data, personal data is never *emitted* in chat output.
   Occurrences are redacted and the event is logged. Retrieval permission
   and emission permission are deliberately different policies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..embedder import tokenize
from ..ingest import split_sentences
from ..schemas import Chunk, Decision, ReasonCode
from .pii import scan_and_redact

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "on",
    "for", "and", "or", "with", "must", "be", "by", "at", "it", "this",
    "that", "per", "as", "from", "all", "may", "can", "will",
}

GROUNDEDNESS_THRESHOLD = 0.45


def content_tokens(text: str) -> set[str]:
    return {t for t in tokenize(text) if t not in STOPWORDS and len(t) > 1}


def sentence_grounded(sentence: str, chunks: list[Chunk]) -> bool:
    tokens = content_tokens(sentence)
    if not tokens:
        return True
    corpus_tokens: set[str] = set()
    for chunk in chunks:
        corpus_tokens |= content_tokens(chunk.text)
    overlap = len(tokens & corpus_tokens) / len(tokens)
    return overlap >= GROUNDEDNESS_THRESHOLD


@dataclass
class OutputScreenResult:
    decision: Decision
    reason_codes: list[ReasonCode] = field(default_factory=list)
    text: str = ""
    detail: str = ""


def screen_output(answer: str, chunks: list[Chunk]) -> OutputScreenResult:
    reasons: list[ReasonCode] = []
    details: list[str] = []

    sentences = split_sentences(answer) or [answer]
    kept = [s for s in sentences if sentence_grounded(s, chunks)]
    dropped = len(sentences) - len(kept)
    if dropped:
        reasons.append(ReasonCode.UNGROUNDED_ANSWER)
        details.append(f"dropped {dropped} ungrounded sentence(s)")
    if not kept:
        return OutputScreenResult(
            decision=Decision.REFUSE,
            reason_codes=reasons or [ReasonCode.UNGROUNDED_ANSWER],
            text="",
            detail="no grounded content remained after output screening",
        )

    cleaned = " ".join(kept)
    pii = scan_and_redact(cleaned)
    if pii.found:
        reasons.append(ReasonCode.PII_IN_OUTPUT_REDACTED)
        details.append(f"PII redacted from output: kinds={pii.kinds}")
        cleaned = pii.text

    if re.fullmatch(r"(\[REDACTED:[A-Z_]+\][\s.,;]*)+", cleaned.strip()):
        return OutputScreenResult(
            decision=Decision.REFUSE,
            reason_codes=reasons,
            text="",
            detail="answer consisted entirely of PII; refused",
        )

    decision = Decision.ALLOW_WITH_REDACTION if reasons else Decision.ALLOW
    if not reasons:
        reasons.append(ReasonCode.ANSWER_OK)
    return OutputScreenResult(
        decision=decision,
        reason_codes=reasons,
        text=cleaned,
        detail="; ".join(details) or "output passed screening",
    )
