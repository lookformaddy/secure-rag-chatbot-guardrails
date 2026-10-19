from secure_rag.guardrails.output_screen import (
    screen_output,
    sentence_grounded,
)
from secure_rag.schemas import Chunk, Decision, ReasonCode, Role


def _chunk(text: str) -> Chunk:
    return Chunk(
        chunk_id="c1",
        doc_id="d1",
        title="Doc",
        department="IT",
        classification="internal",
        allowed_roles=[Role.EMPLOYEE],
        text=text,
    )


CHUNKS = [
    _chunk(
        "All employees must use multi-factor authentication for company systems. "
        "Passwords must be at least fourteen characters."
    )
]


def test_grounded_sentence_passes():
    assert sentence_grounded(
        "All employees must use multi-factor authentication for company systems.",
        CHUNKS,
    )


def test_ungrounded_sentence_detected():
    assert not sentence_grounded(
        "The company cafeteria serves free lobster every Friday afternoon.",
        CHUNKS,
    )


def test_ungrounded_sentences_are_dropped_not_sent():
    answer = (
        "All employees must use multi-factor authentication for company systems. "
        "The company cafeteria serves free lobster every Friday afternoon."
    )
    result = screen_output(answer, CHUNKS)
    assert result.decision in (Decision.ALLOW, Decision.ALLOW_WITH_REDACTION)
    assert "lobster" not in result.text
    assert ReasonCode.UNGROUNDED_ANSWER in result.reason_codes


def test_fully_ungrounded_answer_is_refused():
    result = screen_output(
        "The moon landing budget was doubled by the cafeteria committee.", CHUNKS
    )
    assert result.decision == Decision.REFUSE
    assert result.text == ""


def test_pii_in_output_is_redacted():
    chunks = [
        _chunk(
            "Priya Natarajan, recruiting coordinator, email priya.natarajan@example.com, "
            "phone 415-555-0134."
        )
    ]
    result = screen_output(
        "Priya Natarajan, recruiting coordinator, email priya.natarajan@example.com, "
        "phone 415-555-0134.",
        chunks,
    )
    assert result.decision == Decision.ALLOW_WITH_REDACTION
    assert ReasonCode.PII_IN_OUTPUT_REDACTED in result.reason_codes
    assert "priya.natarajan@example.com" not in result.text
    assert "415-555-0134" not in result.text
    assert "recruiting coordinator" in result.text
