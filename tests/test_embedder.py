import math

from secure_rag.embedder import HashingEmbedder, cosine


def test_deterministic():
    emb = HashingEmbedder()
    assert emb.embed("paid time off policy") == emb.embed("paid time off policy")


def test_normalized():
    emb = HashingEmbedder()
    vec = emb.embed("multi-factor authentication is required")
    assert math.isclose(math.sqrt(sum(v * v for v in vec)), 1.0, rel_tol=1e-6)


def test_related_text_scores_higher_than_unrelated():
    emb = HashingEmbedder()
    q = emb.embed("how many days of paid time off do employees receive")
    related = emb.embed("employees receive fifteen days of paid time off per year")
    unrelated = emb.embed("the cloud vendor agreement renews in march")
    assert cosine(q, related) > cosine(q, unrelated)


def test_empty_text_is_zero_vector():
    emb = HashingEmbedder()
    assert all(v == 0.0 for v in emb.embed(""))
