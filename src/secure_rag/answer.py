"""Grounded answer assembly.

This reference implementation composes answers extractively: it selects the
sentences from the retrieved chunks that best match the query and returns
them verbatim with citations. Extractive assembly makes groundedness a
structural property — the generator cannot invent facts — which is exactly
the posture an enterprise deployment wants before swapping in an LLM behind
the same guardrail contract (the output screen stays necessary either way,
because an LLM *can* invent facts and *can* copy PII).
"""

from __future__ import annotations

from .embedder import tokenize
from .guardrails.output_screen import content_tokens
from .ingest import split_sentences
from .schemas import Chunk, Citation

MAX_ANSWER_SENTENCES = 4


def build_answer(query: str, chunks: list[Chunk]) -> tuple[str, list[Citation]]:
    q_tokens = content_tokens(query)
    scored: list[tuple[float, str, Chunk]] = []
    seen: set[str] = set()
    for chunk in chunks:
        for sentence in split_sentences(chunk.text):
            if sentence in seen:
                continue
            seen.add(sentence)
            s_tokens = content_tokens(sentence)
            if not s_tokens:
                continue
            overlap = len(q_tokens & s_tokens) / max(len(s_tokens), 1)
            # Small bonus for raw query-token coverage keeps answers on-topic.
            coverage = len(q_tokens & s_tokens) / max(len(q_tokens), 1)
            scored.append((overlap + coverage, sentence, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    picked = scored[:MAX_ANSWER_SENTENCES]
    if not picked:
        return "", []
    answer = " ".join(sentence for _, sentence, _ in picked)
    citations: list[Citation] = []
    seen_chunks: set[str] = set()
    for _, _, chunk in picked:
        if chunk.chunk_id not in seen_chunks:
            seen_chunks.add(chunk.chunk_id)
            citations.append(
                Citation(doc_id=chunk.doc_id, title=chunk.title, chunk_id=chunk.chunk_id)
            )
    return answer, citations
