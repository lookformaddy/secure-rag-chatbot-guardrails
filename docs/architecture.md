# Architecture

## Pipeline stages

Every chat request flows through five stages under a single `trace_id`.
Each stage emits an audit event (`stage`, `decision`, `reason_code`, user,
role, non-sensitive detail).

### 1. Input screening (`guardrails/input_screen.py`)
Ordered checks:
1. **Prompt-injection patterns** — instruction override, system-prompt
   extraction, persona hijack, jailbreak keywords, delimiter smuggling,
   policy bypass, fake authority. Any match → `BLOCK / INJECTION_DETECTED`.
2. **Sensitive-disclosure patterns** — requests naming an individual (a
   capitalized two-word name) together with contact data, individual salary,
   credentials, or a bulk directory dump → `BLOCK /
   SENSITIVE_DISCLOSURE_REQUEST`. The name-capitalization heuristic keeps
   role-level questions ("director compensation band") out of this layer;
   authorization for those is the ACL layer's job.
3. **Pasted PII** — detected PII is redacted in place and the request
   proceeds (`ALLOW_WITH_REDACTION / PII_IN_INPUT_REDACTED`).

### 2. Ingestion & index (`ingest.py`, `corpus.py`)
Documents are split into sentence-aligned chunks (max ~60 words, one
sentence of overlap) so chunks never cut a sentence — the groundedness check
depends on sentence integrity. ACL metadata (`allowed_roles`,
`classification`, department) is copied onto every chunk. Embeddings come
from a deterministic hashed unigram/bigram embedder (stopword-filtered,
unsigned counts, L2-normalized), so scores are a pure lexical-overlap
measure and fully reproducible.

### 3. Retrieval (`retrieval.py`)
The candidate set is **filtered by role before scoring**:
`role_can_access(role, chunk)` must hold for a chunk to be scored at all.
`admin` sees everything. The retriever reports `filtered_out` (a count,
never identities) so the policy layer can audit ACL activity.

Two relevance gates then apply:
- cosine similarity ≥ 0.10 against the query embedding;
- a collision-free lexical gate in the service layer: a surviving chunk
  must share ≥ 2 exact content tokens with the query (hashed-vector scores
  can be inflated by hash collisions; exact-token overlap cannot).

### 4. Retrieval policy (`service.py`)
- No surviving chunks and nothing relevant exists for anyone →
  `REFUSE / OUT_OF_SCOPE`.
- No surviving chunks but relevant material exists in the index →
  `REFUSE / NO_ACCESSIBLE_CONTENT`. The user-facing wording is generic in
  both cases; only the audit log distinguishes them.
- Chunks excluded by ACL → an `ACCESS_FILTERED_CHUNKS` event is logged
  (counts only).

### 5. Answer assembly & output screening (`answer.py`, `guardrails/output_screen.py`)
Answers are assembled extractively: sentences from the surviving chunks are
ranked by query-token overlap and returned verbatim with citations. The
output screen then independently verifies:
- **Groundedness** — each answer sentence's content tokens must overlap the
  retrieved chunk tokens by ≥ 45%; failing sentences are dropped
  (`UNGROUNDED_ANSWER`); if none remain, the answer is refused.
- **PII emission** — any PII in the final text is redacted
  (`PII_IN_OUTPUT_REDACTED`) regardless of the requester's retrieval
  rights; an answer that is *only* PII is refused outright.

## Data model

- `Document` — source text + ACL metadata (as a connector would supply).
- `Chunk` — indexed unit; carries its document's ACL.
- `GuardrailEvent` — one pipeline decision; in-memory store with an
  optional JSONL sink (`AuditLog(jsonl_path=...)`) for shipping to a SIEM.

## Trust boundaries

- **Role is a request-context assertion**, never parsed from message text.
  In production this maps to IdP claims; the fake-authority input patterns
  exist to catch and log spoofing attempts in text.
- **Retrieved text is data, never instructions.** The assembler quotes
  sentences; it cannot execute them. This structurally blunts indirect
  (document-borne) injection for this implementation.
- **Admin telemetry is itself access-controlled** (`X-Role: admin` header
  check) because guardrail events reveal what people tried to ask.

## Extension seams

| Seam | Swap |
|---|---|
| `HashingEmbedder` | Hosted embedding model (same `embed()` contract) |
| `VectorIndex` | pgvector / OpenSearch / managed vector DB |
| `build_answer` | LLM generation — output screen contract unchanged |
| `AuditLog` | OpenTelemetry exporter / SIEM forwarder |
| Role assertion | OIDC/JWT claim validation middleware |
