"""Input screening: the first guardrail every message passes through.

Three checks, in order:
1. Prompt-injection patterns — instruction-override, persona hijack,
   system-prompt extraction, and delimiter smuggling. Matches BLOCK.
2. Sensitive-disclosure requests — asking for another person's personal
   data or for restricted categories (salary of an individual, passwords).
   These BLOCK as disclosure attempts; the role-ACL would usually stop the
   retrieval anyway, but blocking at the edge gives a clean audit signal.
3. PII pasted by the user — redacted (not blocked) so a user can still ask
   about their own data, and the redaction is logged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..schemas import Decision, ReasonCode
from .pii import scan_and_redact

_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("override_instructions", re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I)),
    ("override_rules", re.compile(r"disregard\s+(your\s+)?(rules|guidelines|instructions|policy)", re.I)),
    ("system_prompt_extraction", re.compile(r"(reveal|show|print|repeat)\s+(me\s+)?(your\s+)?(system\s+prompt|initial\s+instructions)", re.I)),
    ("persona_hijack", re.compile(r"you\s+are\s+now\s+(a|an|in)\b.{0,40}(mode|persona|assistant)", re.I)),
    ("jailbreak_keyword", re.compile(r"\b(DAN|jailbreak|developer\s+mode|god\s+mode)\b", re.I)),
    ("delimiter_smuggling", re.compile(r"(</?(system|assistant|instruction)>|\[INST\]|\{\{\s*system)", re.I)),
    ("policy_bypass", re.compile(r"(bypass|override|disable)\s+(the\s+)?(guardrails?|filters?|safety|access\s+controls?)", re.I)),
    ("fake_authority", re.compile(r"(as\s+an?\s+admin|i\s+am\s+the\s+(ceo|cto|administrator))\b.{0,60}(show|give|list|tell)", re.I)),
]

# Disclosure patterns target a NAMED individual (capitalized two-word name),
# so legitimate role-level questions ("salary band for directors",
# "email for the support team") are not false-positived.
_DISCLOSURE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("personal_contact", re.compile(r"(email|phone|address|ssn|social\s+security)\s+(of|for)\s+[A-Z][a-z]+\s+[A-Z][a-z]+")),
    ("individual_salary", re.compile(r"(salary|compensation|pay)\s+of\s+[A-Z][a-z]+\s+[A-Z][a-z]+")),
    ("credential_request", re.compile(r"\b(password|api\s+key|secret\s+key|access\s+token)\s+(for|of|to)\b", re.I)),
    ("dump_directory", re.compile(r"(list|dump|export|show)\s+(all\s+)?(the\s+)?(employee\s+)?(directory|contacts|emails|phone\s+numbers)", re.I)),
]


@dataclass
class InputScreenResult:
    decision: Decision
    reason_codes: list[ReasonCode] = field(default_factory=list)
    sanitized_text: str = ""
    detail: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision in (Decision.ALLOW, Decision.ALLOW_WITH_REDACTION)


def screen_input(message: str) -> InputScreenResult:
    for name, pattern in _INJECTION_PATTERNS:
        if pattern.search(message):
            return InputScreenResult(
                decision=Decision.BLOCK,
                reason_codes=[ReasonCode.INJECTION_DETECTED],
                sanitized_text="",
                detail=f"prompt-injection pattern matched: {name}",
            )
    for name, pattern in _DISCLOSURE_PATTERNS:
        if pattern.search(message):
            return InputScreenResult(
                decision=Decision.BLOCK,
                reason_codes=[ReasonCode.SENSITIVE_DISCLOSURE_REQUEST],
                sanitized_text="",
                detail=f"sensitive-disclosure pattern matched: {name}",
            )
    pii = scan_and_redact(message)
    if pii.found:
        return InputScreenResult(
            decision=Decision.ALLOW_WITH_REDACTION,
            reason_codes=[ReasonCode.PII_IN_INPUT_REDACTED],
            sanitized_text=pii.text,
            detail=f"PII redacted from user input: kinds={pii.kinds}",
        )
    return InputScreenResult(
        decision=Decision.ALLOW,
        reason_codes=[ReasonCode.OK],
        sanitized_text=message,
        detail="input passed screening",
    )
