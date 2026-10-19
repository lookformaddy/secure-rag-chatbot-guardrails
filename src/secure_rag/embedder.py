"""A local, deterministic text embedder.

Production systems would call a hosted embedding model. For a self-contained,
reproducible project we use a hashed bag-of-words / bigram embedding:

* tokenize -> unigrams + adjacent bigrams (stopwords removed)
* hash each feature with MD5 into a fixed-dimension space
* count-weight (unsigned — similarity stays a pure overlap measure, with
  no sign cancellations), then L2-normalize

Properties that matter here:
* Deterministic — the same text always yields the same vector (seed-free),
  so tests and evals are exactly reproducible on any machine.
* Local — no API keys, no network, no data leaving the process.
* Lexically sensitive — good enough for a curated enterprise corpus where
  vocabulary overlap is a strong relevance signal.
"""

from __future__ import annotations

import hashlib
import math
import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Function words carry no topical signal; left in, they inflate the cosine
# similarity of unrelated texts (everything shares "the", "is", "for") and
# blur the relevance threshold the refusal policy depends on.
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "of", "to",
    "in", "on", "for", "and", "or", "with", "by", "at", "it", "its", "this",
    "that", "what", "how", "do", "does", "did", "i", "you", "we", "they",
    "me", "my", "your", "our", "their", "can", "could", "should", "would",
    "will", "shall", "may", "might", "must", "as", "from", "about", "into",
    "there", "here", "when", "where", "who", "whom", "which",
}


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class HashingEmbedder:
    def __init__(self, dim: int = 1024) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim

    def _features(self, text: str) -> list[str]:
        tokens = [t for t in tokenize(text) if t not in _STOPWORDS]
        feats = list(tokens)
        feats.extend(f"{a}::{b}" for a, b in zip(tokens, tokens[1:]))
        return feats

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for feat in self._features(text):
            digest = hashlib.md5(feat.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity for L2-normalized vectors (a dot product)."""
    return sum(x * y for x, y in zip(a, b))
