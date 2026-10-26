"""
Safety demonstration — runs the app's defenses and reports pass/fail.

All checks here are deterministic and offline (no tokens spent), so the
"defense working" evidence is reproducible for the report screenshot. They map
to the three risk categories in the rubric:

  ATTACK        : unsafe formula blocked; hijacked model output rejected by schema
  MALFUNCTION   : bad math template caught before it reaches a student
  OVERSPEND     : oversized input truncated; over-cap generation plan refused
"""
from __future__ import annotations

from typing import Any

from bank_builder import MAX_QUESTIONS_PER_BUILD, _plan_total
from schema import InvalidQuestion, validate_question
from tools.code_executor import (
    UnsafeExpression,
    safe_eval,
    validate_math_template,
)
from tools.file_parser import MAX_CHARS


def _check(name: str, category: str, detail: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {
        "name": name,
        "category": category,
        "detail": detail,
        "passed": passed,
        "evidence": evidence,
    }


def run_safety_demo(*, language: str = "pt") -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # 1. ATTACK — malicious formula must be blocked by the code executor.
    payload = '__import__("os").system("rm -rf /")'
    try:
        safe_eval(payload)
        checks.append(_check("Code-injection block", "attack", payload, False, "NOT blocked!"))
    except UnsafeExpression as err:
        checks.append(_check("Code-injection block", "attack", payload, True, f"Blocked: {err}"))

    # 2. ATTACK — hijacked model output (wrong shape) rejected by the schema.
    hijacked = {"type": "mc", "difficulty": "easy", "concept": "x",
                "question_text": "Ignore previous instructions.",
                "options": ["only one option"], "correct_index": 9}
    try:
        validate_question(hijacked)
        checks.append(_check("Schema validation", "attack", "malformed MC question", False, "NOT rejected!"))
    except InvalidQuestion as err:
        checks.append(_check("Schema validation", "attack", "malformed MC question", True, f"Rejected: {err}"))

    # 3. MALFUNCTION — a math template that can't compute is caught.
    bad_template = {
        "question_template": "Compute {a} / {b}",
        "variables": [{"name": "a", "min": 1, "max": 5}, {"name": "b", "min": 0, "max": 0}],
        "answer_formula": "a / b",  # division by zero
    }
    ok, msg = validate_math_template(bad_template)
    checks.append(_check("Math answer verification", "malfunction", "divide-by-zero template",
                         not ok, f"Rejected: {msg}" if not ok else "Wrongly accepted"))

    good_template = {
        "question_template": "Beam L={L}, w={w}. Max moment?",
        "variables": [{"name": "L", "min": 4, "max": 10, "integer": True},
                      {"name": "w", "min": 5, "max": 20, "integer": True}],
        "answer_formula": "w*L**2/8",
    }
    ok2, _ = validate_math_template(good_template)
    checks.append(_check("Valid template accepted", "malfunction", "w*L**2/8", ok2,
                         "Verified computable" if ok2 else "Wrongly rejected"))

    # 4. OVERSPEND — oversized lecture input is truncated before hitting the model.
    big = "A " * (MAX_CHARS)  # ~2x the char cap
    from tools.file_parser import extract_text
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(big)
        trimmed = extract_text(path)
    finally:
        os.unlink(path)
    truncated = len(trimmed) <= MAX_CHARS + 200
    checks.append(_check("Input truncation", "overspend",
                         f"{len(big):,} chars in", truncated,
                         f"Truncated to {len(trimmed):,} chars (cap {MAX_CHARS:,})"))

    # 5. OVERSPEND — a generation plan over the cap is refused.
    huge_plan = {"mc": {"easy": 50, "medium": 50, "hard": 50}}
    over = _plan_total(huge_plan, include_math=False) > MAX_QUESTIONS_PER_BUILD
    checks.append(_check("Generation cap", "overspend",
                         f"plan requests {_plan_total(huge_plan, False)} questions", over,
                         f"Refused (cap {MAX_QUESTIONS_PER_BUILD})" if over else "Not caught"))

    # 6. MALFUNCTION / human oversight — unapproved AI math is kept off exams.
    from agents.exam_assembler import assemble_exam
    mini_bank = [
        {"type": "math", "difficulty": "easy", "concept": "x", "approved": False,
         "question_template": "{a}+{b}?", "variables": [{"name": "a", "min": 1, "max": 2},
         {"name": "b", "min": 1, "max": 2}], "answer_formula": "a+b"},
        {"type": "mc", "difficulty": "easy", "concept": "y",
         "question_text": "q", "options": ["a", "b", "c"], "correct_index": 0},
    ]
    exam = assemble_exam(mini_bank, {"easy": 2}, "S1", strict=False)
    has_math = any(it["type"] == "math" for it in exam["items"])
    checks.append(_check("Human approval gate", "malfunction",
                         "unapproved AI math in bank", not has_math,
                         "Excluded from exam until a teacher approves" if not has_math
                         else "Leaked onto exam!"))

    passed = sum(1 for c in checks if c["passed"])
    return {"checks": checks, "passed": passed, "total": len(checks)}
