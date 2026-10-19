"""Ingestion pipeline: documents -> sentence-aware chunks -> embedded index.

Chunking strategy: group whole sentences into chunks of at most
``max_words`` words with a one-sentence overlap, so a chunk never cuts a
sentence in half (which would corrupt both retrieval and the groundedness
check downstream). ACL metadata is copied onto every chunk at ingest time.
"""

from __future__ import annotations

import re

from .embedder import HashingEmbedder
from .schemas import Chunk, Document

_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]")


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_RE.findall(text)]
    return [p for p in parts if p]


def chunk_document(doc: Document, max_words: int = 60, overlap_sentences: int = 1) -> list[Chunk]:
    sentences = split_sentences(doc.text)
    chunks: list[Chunk] = []
    current: list[str] = []
    current_words = 0

    def flush(sent_list: list[str]) -> None:
        if not sent_list:
            return
        chunks.append(
            Chunk(
                chunk_id=f"{doc.doc_id}-c{len(chunks)}",
                doc_id=doc.doc_id,
                title=doc.title,
                department=doc.department,
                classification=doc.classification,
                allowed_roles=list(doc.allowed_roles),
                text=" ".join(sent_list),
            )
        )

    for sent in sentences:
        n = len(sent.split())
        if current and current_words + n > max_words:
            flush(current)
            current = current[-overlap_sentences:] if overlap_sentences else []
            current_words = sum(len(s.split()) for s in current)
        current.append(sent)
        current_words += n
    flush(current)
    return chunks


class VectorIndex:
    """In-memory vector index over ACL-tagged chunks."""

    def __init__(self, embedder: HashingEmbedder | None = None) -> None:
        self.embedder = embedder or HashingEmbedder()
        self.chunks: list[Chunk] = []

    def add_documents(self, documents: list[Document]) -> int:
        added = 0
        for doc in documents:
            for chunk in chunk_document(doc):
                chunk.embedding = self.embedder.embed(chunk.text)
                self.chunks.append(chunk)
                added += 1
        return added

    def __len__(self) -> int:
        return len(self.chunks)
