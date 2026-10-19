"""The core security proof: for every role and a battery of probing queries,
retrieval must NEVER surface a chunk the role is not allowed to see."""

import pytest

from secure_rag.corpus import synthetic_corpus
from secure_rag.ingest import VectorIndex
from secure_rag.retrieval import Retriever, role_can_access
from secure_rag.schemas import Role

PROBES = [
    "director compensation band salary 2026",
    "compensation bands confidential salary ranges",
    "internal contact directory email phone employee",
    "product roadmap FY27 themes confidential",
    "vendor contract pricing committed spend termination",
    "paid time off remote work handbook",
    "on-call rotation stipend incident",
    "salary",
    "directory",
    "roadmap",
    "vendor",
    "",
]


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    index = VectorIndex()
    index.add_documents(synthetic_corpus())
    return Retriever(index)


@pytest.mark.parametrize("role", list(Role))
@pytest.mark.parametrize("query", PROBES)
def test_retrieval_never_leaks_unauthorized_chunks(retriever, role, query):
    result = retriever.retrieve(query, role, top_k=10, threshold=0.0)
    for chunk in result.chunks:
        assert role_can_access(role, chunk), (
            f"LEAK: role {role} received chunk {chunk.chunk_id} "
            f"({chunk.title}) for query {query!r}"
        )


def test_restricted_docs_invisible_to_employee(retriever):
    result = retriever.retrieve("director compensation band 2026", Role.EMPLOYEE, top_k=10, threshold=0.0)
    titles = {c.title for c in result.chunks}
    assert "Compensation Bands 2026" not in titles
    assert "Internal Contact Directory (Restricted)" not in titles
    assert result.filtered_out > 0


def test_filter_actually_removes_top_matches(retriever):
    """Without the filter, the salary doc IS the top match for this query —
    proving the filter (not weak ranking) is what protects it."""
    raw = retriever.raw_top_matches("director compensation band 2026", top_k=1)
    assert raw and raw[0].doc_id == "doc-salary-bands"
    filtered = retriever.retrieve("director compensation band 2026", Role.EMPLOYEE, top_k=1, threshold=0.0)
    assert all(c.doc_id != "doc-salary-bands" for c in filtered.chunks)


def test_admin_sees_everything(retriever):
    result = retriever.retrieve("director compensation band 2026", Role.ADMIN, top_k=4)
    assert any(c.doc_id == "doc-salary-bands" for c in result.chunks)
    assert result.filtered_out == 0


def test_hr_can_retrieve_salary_bands(retriever):
    result = retriever.retrieve("director compensation band 2026", Role.HR, top_k=4)
    assert any(c.doc_id == "doc-salary-bands" for c in result.chunks)
