"""Secure RAG Chatbot with Guardrails.

An enterprise retrieval-augmented generation service where security is not a
filter bolted on at the end but a property of every stage:

    ingest -> ACL-tagged index -> input screening -> permission-enforcing
    retrieval -> grounded answer assembly -> output screening -> audit log
"""

__version__ = "1.0.0"
