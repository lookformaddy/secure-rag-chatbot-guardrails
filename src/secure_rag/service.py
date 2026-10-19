"""Chat service: orchestrates the full guarded pipeline.

Pipeline (every stage audited under one trace id):
  1. input screening      -> block injections / disclosure attempts, redact PII
  2. retrieval            -> permission-filtered BEFORE ranking
  3. retrieval policy     -> refuse when nothing accessible is relevant;
                             log when chunks were excluded by ACL
  4. answer assembly      -> extractive, citation-carrying
  5. output screening     -> groundedness verification + PII emission control

Refusal messages are deliberately generic: they never reveal whether a
restricted document exists, what it is called, or who may see it.
"""

from __future__ import annotations

import uuid

from .answer import build_answer
from .audit import AuditLog, GuardrailEvent
from .corpus import synthetic_corpus
from .guardrails.input_screen import screen_input
from .guardrails.output_screen import content_tokens, screen_output
from .ingest import VectorIndex
from .retrieval import Retriever
from .schemas import ChatRequest, ChatResponse, Decision, ReasonCode

REFUSAL_BLOCKED = (
    "I can't help with that request. It conflicts with the assistant's usage "
    "policy, and the attempt has been logged for review."
)
REFUSAL_NO_ACCESS = (
    "I couldn't find anything in the knowledge base that you have access to "
    "and that answers this question."
)
REFUSAL_OUT_OF_SCOPE = (
    "That question is outside the scope of the company knowledge base I can "
    "search. Try asking about company policies, benefits, travel, or IT."
)
REFUSAL_UNGROUNDED = (
    "I found related material but couldn't assemble an answer I can stand "
    "behind, so I'd rather not guess."
)


class ChatService:
    def __init__(self, audit: AuditLog | None = None) -> None:
        self.index = VectorIndex()
        self.index.add_documents(synthetic_corpus())
        self.retriever = Retriever(self.index)
        self.audit = audit or AuditLog()

    def _log(self, trace_id, stage, decision, reason, req, detail) -> None:
        self.audit.record(
            GuardrailEvent(
                trace_id=trace_id,
                stage=stage,
                decision=decision,
                reason_code=reason,
                user_id=req.user_id,
                role=req.role,
                detail=detail,
            )
        )

    def chat(self, req: ChatRequest) -> ChatResponse:
        trace_id = uuid.uuid4().hex[:12]
        reasons: list[ReasonCode] = []

        # ---- Stage 1: input screening ------------------------------------
        screened = screen_input(req.message)
        self._log(trace_id, "input_screen", screened.decision,
                  screened.reason_codes[0], req, screened.detail)
        reasons.extend(screened.reason_codes)
        if not screened.allowed:
            return ChatResponse(
                trace_id=trace_id,
                decision=Decision.BLOCK,
                answer=REFUSAL_BLOCKED,
                reason_codes=reasons,
            )

        # ---- Stage 2 + 3: permission-enforcing retrieval & policy --------
        result = self.retriever.retrieve(screened.sanitized_text, req.role)
        # Lexical sanity gate: hashed-vector scores can be inflated by hash
        # collisions, so a "relevant" chunk must also share at least two
        # exact content tokens with the query. Collision-free and cheap.
        q_tokens = content_tokens(screened.sanitized_text)
        chunks = [
            c for c in result.chunks
            if len(q_tokens & content_tokens(c.text)) >= 2
        ]
        if result.filtered_out:
            self._log(trace_id, "retrieval_policy", Decision.ALLOW,
                      ReasonCode.ACCESS_FILTERED_CHUNKS, req,
                      f"{result.filtered_out} chunk(s) excluded by ACL for role "
                      f"{req.role.value} (identities not disclosed)")
        if not chunks:
            # Distinguish "relevant material exists but not for this role"
            # from "nothing relevant exists at all" — in the audit log only;
            # refusal wording stays generic either way.
            raw_relevant = self.retriever.has_match_above_threshold(
                screened.sanitized_text
            )
            if raw_relevant:
                code = ReasonCode.NO_ACCESSIBLE_CONTENT
                self._log(trace_id, "retrieval_policy", Decision.REFUSE, code, req,
                          "no permitted chunks above the relevance threshold")
                return ChatResponse(trace_id=trace_id, decision=Decision.REFUSE,
                                    answer=REFUSAL_NO_ACCESS, reason_codes=reasons + [code])
            code = ReasonCode.OUT_OF_SCOPE
            self._log(trace_id, "retrieval_policy", Decision.REFUSE, code, req,
                      "no relevant chunks above the relevance threshold")
            return ChatResponse(trace_id=trace_id, decision=Decision.REFUSE,
                                answer=REFUSAL_OUT_OF_SCOPE, reason_codes=reasons + [code])

        # ---- Stage 4: grounded answer assembly ---------------------------
        answer, citations = build_answer(screened.sanitized_text, chunks)
        if not answer:
            code = ReasonCode.OUT_OF_SCOPE
            self._log(trace_id, "answer_assembly", Decision.REFUSE, code, req,
                      "retrieved chunks contained no answer-bearing sentences")
            return ChatResponse(trace_id=trace_id, decision=Decision.REFUSE,
                                answer=REFUSAL_OUT_OF_SCOPE, reason_codes=reasons + [code])

        # ---- Stage 5: output screening -----------------------------------
        out = screen_output(answer, chunks)
        self._log(trace_id, "output_screen", out.decision,
                  out.reason_codes[0], req, out.detail)
        reasons.extend(out.reason_codes)
        if out.decision == Decision.REFUSE:
            return ChatResponse(trace_id=trace_id, decision=Decision.REFUSE,
                                answer=REFUSAL_UNGROUNDED, reason_codes=reasons)
        decision = (
            Decision.ALLOW_WITH_REDACTION
            if Decision.ALLOW_WITH_REDACTION in (screened.decision, out.decision)
            else Decision.ALLOW
        )
        return ChatResponse(
            trace_id=trace_id,
            decision=decision,
            answer=out.text,
            citations=citations,
            reason_codes=reasons,
        )
