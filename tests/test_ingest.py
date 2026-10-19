from secure_rag.corpus import synthetic_corpus
from secure_rag.ingest import VectorIndex, chunk_document, split_sentences
from secure_rag.schemas import Role


def test_corpus_documents_have_acl_metadata():
    for doc in synthetic_corpus():
        assert doc.allowed_roles, doc.doc_id
        assert doc.classification in {
            "public-internal", "internal", "confidential", "restricted"
        }


def test_chunking_never_splits_sentences():
    doc = synthetic_corpus()[0]
    for chunk in chunk_document(doc):
        for sentence in split_sentences(chunk.text):
            assert sentence in doc.text


def test_chunks_inherit_document_acl():
    salary_doc = next(d for d in synthetic_corpus() if d.doc_id == "doc-salary-bands")
    chunks = chunk_document(salary_doc)
    assert chunks
    for chunk in chunks:
        assert chunk.allowed_roles == [Role.HR, Role.ADMIN]
        assert chunk.classification == "restricted"


def test_index_embeds_every_chunk():
    index = VectorIndex()
    n = index.add_documents(synthetic_corpus())
    assert n == len(index) > 0
    assert all(len(c.embedding) == index.embedder.dim for c in index.chunks)
