"""
Agent 4: Exam Assembler (deterministic — no LLM, so it is free to run).

Given a question bank, a difficulty mix, and a list of students, it builds a
unique exam + answer key per student:
  - samples questions to the mix (e.g. 3 easy / 3 medium / 4 hard) without repeats
  - shuffles question order
  - shuffles multiple-choice options and recomputes the correct index
  - instantiates each math template with fresh random numbers (via code_executor)

Because this step costs no tokens, the cost of a whole class — or many terms —
is just the one-time cost of authoring the bank. That is the core of the
tokenomics story.
"""
from __future__ import annotations

import random
from typing import Any

from tools.code_executor import instantiate_math_variant

_LETTERS = "ABCDEFGH"


class NotEnoughQuestions(ValueError):
    pass


def _student_rng(base_seed: int | str, student_id: str) -> random.Random:
    return random.Random(f"{base_seed}::{student_id}")


def _pool_by_difficulty(
    bank: list[dict[str, Any]], difficulty: str, types: set[str] | None
) -> list[dict[str, Any]]:
    pool = []
    for q in bank:
        if q.get("difficulty") != difficulty:
            continue
        if types is not None and q.get("type") not in types:
            continue
        # Human-in-the-loop: AI-written math must be approved by a teacher before
        # it can appear on a student's exam. Non-math questions need no gate.
        if q.get("type") == "math" and not q.get("approved", False):
            continue
        pool.append(q)
    return pool


def assemble_exam(
    bank: list[dict[str, Any]],
    mix: dict[str, int],
    student_id: str,
    *,
    base_seed: int | str = 42,
    types: set[str] | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Build one student's exam + answer key.

    `mix` maps difficulty -> number of questions, e.g. {"easy":3,"medium":3,"hard":4}.
    If a tier has fewer questions than requested and strict=False, it takes what's
    available and records a shortfall; strict=True raises instead.
    """
    rng = _student_rng(base_seed, student_id)
    chosen: list[dict[str, Any]] = []
    shortfalls: dict[str, int] = {}

    for difficulty in ("easy", "medium", "hard"):
        want = int(mix.get(difficulty, 0))
        if want <= 0:
            continue
        pool = _pool_by_difficulty(bank, difficulty, types)
        if len(pool) < want:
            if strict:
                raise NotEnoughQuestions(
                    f"Need {want} '{difficulty}' questions but bank has {len(pool)}."
                )
            shortfalls[difficulty] = want - len(pool)
            picked = list(pool)
        else:
            picked = rng.sample(pool, want)
        chosen.extend(picked)

    rng.shuffle(chosen)

    exam_items: list[dict[str, Any]] = []
    answer_key: list[dict[str, Any]] = []

    for i, q in enumerate(chosen, start=1):
        qtype = q["type"]
        qid = q.get("id")
        if qtype == "mc":
            opts = list(enumerate(q["options"]))  # (orig_index, text)
            rng.shuffle(opts)
            shuffled = [text for _, text in opts]
            new_correct = next(
                pos for pos, (orig, _) in enumerate(opts) if orig == q["correct_index"]
            )
            exam_items.append(
                {
                    "number": i,
                    "type": "mc",
                    "concept": q["concept"],
                    "difficulty": q["difficulty"],
                    "question_text": q["question_text"],
                    "options": shuffled,
                }
            )
            answer_key.append(
                {
                    "number": i,
                    "qid": qid,
                    "type": "mc",
                    "correct_letter": _LETTERS[new_correct],
                    "correct_answer": shuffled[new_correct],
                }
            )

        elif qtype == "short":
            exam_items.append(
                {
                    "number": i,
                    "type": "short",
                    "concept": q["concept"],
                    "difficulty": q["difficulty"],
                    "question_text": q["question_text"],
                }
            )
            answer_key.append(
                {"number": i, "qid": qid, "type": "short", "model_answer": q["answer"]}
            )

        elif qtype == "math":
            variant = instantiate_math_variant(q, rng)
            exam_items.append(
                {
                    "number": i,
                    "type": "math",
                    "concept": q["concept"],
                    "difficulty": q["difficulty"],
                    "question_text": variant["question_text"],
                }
            )
            answer_key.append(
                {
                    "number": i,
                    "qid": qid,
                    "type": "math",
                    "answer": variant["answer"],
                    "answer_units": variant["answer_units"],
                    "values": variant["values"],
                }
            )

    return {
        "student_id": student_id,
        "items": exam_items,
        "answer_key": answer_key,
        "shortfalls": shortfalls,
        "num_questions": len(exam_items),
    }


def assemble_class(
    bank: list[dict[str, Any]],
    mix: dict[str, int],
    students: list[str],
    *,
    base_seed: int | str = 42,
    types: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Build unique exams for a list of students."""
    return [
        assemble_exam(bank, mix, s, base_seed=base_seed, types=types)
        for s in students
    ]


def exam_fingerprint(exam: dict[str, Any]) -> str:
    """A compact signature of an exam's questions+order, to show exams differ."""
    import hashlib

    parts = []
    for item in exam["items"]:
        parts.append(item["question_text"])
        if item["type"] == "mc":
            parts.extend(item["options"])
    return hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()[:12]
