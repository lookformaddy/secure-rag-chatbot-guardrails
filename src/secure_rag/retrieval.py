"""Permission-enforcing retrieval.

The security invariant of this project lives here:

    A chunk is a candidate ONLY if the requesting role appears in the
    chunk's allowed_roles. Filtering happens BEFORE ranking, never after.

Filtering after ranking (retrieve-then-hide) leaks information through
ranking side channels and risks the generator seeing forbidden text. Here,
unauthorized chunks do not exist as far as the query is concerned; the
retriever also reports how many chunks were excluded so the policy layer
can log an ACCESS_FILTERED_CHUNKS event without revealing what they were.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .embedder import HashingEmbedder, cosine
from .ingest import VectorIndex
from .schemas import Chunk, Role

RELEVANCE_THRESHOLD = 0.10


@dataclass
class RetrievalResult:
    chunks: list[Chunk] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    filtered_out: int = 0
    total_considered: int = 0

    @property
    def top_score(self) -> float:
        return self.scores[0] if self.scores else 0.0


def role_can_access(role: Role, chunk: Chunk) -> bool:
    return role == Role.ADMIN or role in chunk.allowed_roles


class Retriever:
    def __init__(self, index: VectorIndex, embedder: HashingEmbedder | None = None) -> None:
        self.index = index
        self.embedder = embedder or index.embedder

    def retrieve(
        self,
        query: str,
        role: Role,
        top_k: int = 4,
        threshold: float = RELEVANCE_THRESHOLD,
    ) -> RetrievalResult:
        qvec = self.embedder.embed(query)
        permitted: list[tuple[float, Chunk]] = []
        filtered = 0
        for chunk in self.index.chunks:
            if not role_can_access(role, chunk):
                filtered += 1
                continue
            permitted.append((cosine(qvec, chunk.embedding), chunk))
        permitted.sort(key=lambda pair: pair[0], reverse=True)
        kept = [(s, c) for s, c in permitted if s >= threshold][:top_k]
        return RetrievalResult(
            chunks=[c for _, c in kept],
            scores=[s for s, _ in kept],
            filtered_out=filtered,
            total_considered=len(self.index.chunks),
        )

    def has_match_above_threshold(
        self, query: str, threshold: float = RELEVANCE_THRESHOLD
    ) -> bool:
        """True if ANY chunk (ignoring permissions) clears the threshold.
        Used by the policy layer (audit only) to distinguish 'nothing
        relevant exists' from 'relevant material exists but not for you'."""
        qvec = self.embedder.embed(query)
        return any(
            cosine(qvec, c.embedding) >= threshold for c in self.index.chunks
        )

    def raw_top_matches(self, query: str, top_k: int = 4) -> list[Chunk]:
        """Top matches with NO permission filter. Exists only so tests and the
        admin diagnostics can prove the filter matters — never used to build
        answers."""
        qvec = self.embedder.embed(query)
        scored = sorted(
            ((cosine(qvec, c.embedding), c) for c in self.index.chunks),
            key=lambda pair: pair[0],
            reverse=True,
        )
        return [c for _, c in scored[:top_k]]
