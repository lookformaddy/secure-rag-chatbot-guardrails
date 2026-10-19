#!/usr/bin/env python3
"""Run the security eval set against the chat service (in-process).

Usage:
    PYTHONPATH=src python evals/run_eval.py

Exit code 0 = every case passed. Each case asserts on the pipeline decision,
the reason codes, and on strings that must / must not appear in the answer —
the "must not appear" assertions are the leak tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from secure_rag.schemas import ChatRequest, Role  # noqa: E402
from secure_rag.service import ChatService  # noqa: E402


def main() -> int:
    cases = json.loads((Path(__file__).parent / "eval_set.json").read_text())
    service = ChatService()
    passed, failed = 0, 0
    for case in cases:
        resp = service.chat(
            ChatRequest(
                user_id=f"eval-{case['id']}",
                role=Role(case["role"]),
                message=case["question"],
            )
        )
        problems: list[str] = []
        if resp.decision.value not in case["expect_decision_in"]:
            problems.append(
                f"decision {resp.decision.value} not in {case['expect_decision_in']}"
            )
        for needle in case.get("expect_answer_contains", []):
            if needle.lower() not in resp.answer.lower():
                problems.append(f"answer missing {needle!r}")
        for needle in case.get("expect_answer_not_contains", []):
            if needle.lower() in resp.answer.lower():
                problems.append(f"LEAK: answer contains forbidden {needle!r}")
        codes = {c.value for c in resp.reason_codes}
        for code in case.get("expect_reason_includes", []):
            if code not in codes:
                problems.append(f"reason {code} missing (got {sorted(codes)})")
        status = "PASS" if not problems else "FAIL"
        if problems:
            failed += 1
        else:
            passed += 1
        print(f"[{status}] {case['id']:<26} ({case['category']}) "
              f"decision={resp.decision.value}")
        for p in problems:
            print(f"       - {p}")
    print(f"\n{passed} passed, {failed} failed, {len(cases)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
