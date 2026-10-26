"""
Question schema + validation.

Every question the model produces is validated against these rules before it
enters the bank. Rejecting malformed or hijacked output is one of the safety
defenses (an injection that makes the model return prose or the wrong shape
gets dropped instead of stored).
"""
from __future__ import annotations

from typing import Any

DIFFICULTIES = ("easy", "medium", "hard")
TYPES = ("mc", "short", "math")


class InvalidQuestion(ValueError):
    pass


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise InvalidQuestion(msg)


def validate_question(q: Any) -> dict[str, Any]:
    """Validate and normalize one question dict. Raises InvalidQuestion on failure."""
    _require(isinstance(q, dict), "question must be an object")
    qtype = q.get("type")
    _require(qtype in TYPES, f"type must be one of {TYPES}, got {qtype!r}")
    difficulty = q.get("difficulty")
    _require(difficulty in DIFFICULTIES, f"difficulty must be one of {DIFFICULTIES}")

    concept = str(q.get("concept", "")).strip()
    _require(bool(concept), "concept is required")

    clean: dict[str, Any] = {
        "type": qtype,
        "difficulty": difficulty,
        "concept": concept,
        "language": q.get("language", "pt"),
    }

    if qtype == "mc":
        text = str(q.get("question_text", "")).strip()
        _require(bool(text), "mc question_text is required")
        options = q.get("options")
        _require(
            isinstance(options, list) and 3 <= len(options) <= 6,
            "mc needs 3-6 options",
        )
        options = [str(o).strip() for o in options]
        _require(all(options), "mc options cannot be empty")
        ci = q.get("correct_index")
        _require(
            isinstance(ci, int) and 0 <= ci < len(options),
            "mc correct_index out of range",
        )
        clean.update(question_text=text, options=options, correct_index=ci)

    elif qtype == "short":
        text = str(q.get("question_text", "")).strip()
        _require(bool(text), "short question_text is required")
        answer = str(q.get("answer", "")).strip()
        _require(bool(answer), "short answer is required")
        clean.update(question_text=text, answer=answer)

    elif qtype == "math":
        _require(
            bool(str(q.get("question_template", "")).strip()),
            "math question_template is required",
        )
        _require(
            bool(str(q.get("answer_formula", "")).strip()),
            "math answer_formula is required",
        )
        variables = q.get("variables")
        _require(
            isinstance(variables, list) and len(variables) >= 1,
            "math needs at least one variable",
        )
        for v in variables:
            _require(isinstance(v, dict), "each variable must be an object")
            _require(bool(str(v.get("name", "")).strip()), "variable name required")
            _require("min" in v and "max" in v, "variable needs min and max")
        clean.update(
            question_template=str(q["question_template"]).strip(),
            answer_formula=str(q["answer_formula"]).strip(),
            variables=variables,
            answer_units=str(q.get("answer_units", "")).strip(),
        )

    return clean
