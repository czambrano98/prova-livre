"""
Orchestrator: runs the agent pipeline to build a question bank.

Flow (this is the multi-agent handoff shown in the report diagram):

    lecture text --> [Concept Extractor] --> concepts
    concepts ------> [Question Author]   --> mc + short questions (per difficulty)
    concepts ------> [Math Variant]      --> verified math templates (per difficulty)
    (questions) ---> bank_store (persisted, grows across terms)

The Exam Assembler (free, deterministic) runs later, at exam time.

Overspend defense: the number of questions requested is capped per build, and
the input text is already truncated by the file parser.
"""
from __future__ import annotations

from typing import Any

from agents import concept_extractor, math_variant, question_author
from tools import token_logger

# Overspend guard: hard ceiling on questions requested in a single build.
MAX_QUESTIONS_PER_BUILD = 80

# Default generation plan: counts[type][difficulty].
DEFAULT_PLAN: dict[str, dict[str, int]] = {
    "mc": {"easy": 4, "medium": 4, "hard": 4},
    "short": {"easy": 2, "medium": 2, "hard": 3},
    "math": {"easy": 2, "medium": 2, "hard": 3},
}

DIFFICULTIES = ("easy", "medium", "hard")


def _plan_total(plan: dict[str, dict[str, int]], include_math: bool) -> int:
    total = 0
    for qtype, by_diff in plan.items():
        if qtype == "math" and not include_math:
            continue
        total += sum(by_diff.values())
    return total


def _concepts_to_context(concepts: list[dict[str, Any]], quantitative_only: bool = False) -> str:
    lines = []
    for c in concepts:
        if quantitative_only and not c.get("quantitative"):
            continue
        summary = c.get("summary", "")
        lines.append(f"- {c['topic']}: {summary}")
    return "\n".join(lines)


def build_bank_from_material(
    material_text: str,
    *,
    language: str = "pt",
    plan: dict[str, dict[str, int]] | None = None,
) -> dict[str, Any]:
    """Extract concepts and author a bank. Returns a summary dict (not yet saved)."""
    plan = plan or DEFAULT_PLAN
    run_id = token_logger.start_run()
    try:
        concepts = concept_extractor.extract_concepts(material_text, language=language)
        quantitative = [c for c in concepts if c.get("quantitative")]
        include_math = bool(quantitative) and any(
            plan.get("math", {}).values()
        )

        if _plan_total(plan, include_math) > MAX_QUESTIONS_PER_BUILD:
            raise ValueError(
                f"Plan requests more than the {MAX_QUESTIONS_PER_BUILD}-question cap."
            )

        topics_ctx = _concepts_to_context(concepts)
        quant_ctx = _concepts_to_context(concepts, quantitative_only=True)

        questions: list[dict[str, Any]] = []

        for difficulty in DIFFICULTIES:
            n_mc = plan.get("mc", {}).get(difficulty, 0)
            if n_mc:
                questions += question_author.generate_batch(
                    topics_context=topics_ctx,
                    difficulty=difficulty,
                    qtype="mc",
                    count=n_mc,
                    language=language,
                )
            n_short = plan.get("short", {}).get(difficulty, 0)
            if n_short:
                questions += question_author.generate_batch(
                    topics_context=topics_ctx,
                    difficulty=difficulty,
                    qtype="short",
                    count=n_short,
                    language=language,
                )
            n_math = plan.get("math", {}).get(difficulty, 0)
            if include_math and n_math:
                questions += math_variant.build_math_templates(
                    context=quant_ctx,
                    difficulty=difficulty,
                    count=n_math,
                    language=language,
                )

        usage = token_logger.summarize(run_id)
    finally:
        token_logger.end_run()

    return {
        "run_id": run_id,
        "concepts": concepts,
        "questions": questions,
        "num_questions": len(questions),
        "usage": usage,
    }


def build_bank_from_seeds(
    seed_examples: str,
    *,
    language: str = "pt",
    plan: dict[str, dict[str, int]] | None = None,
) -> dict[str, Any]:
    """Expand a bank from a few teacher-provided example questions."""
    plan = plan or {"mc": {"easy": 2, "medium": 3, "hard": 3}, "short": {"medium": 2}}
    run_id = token_logger.start_run()
    try:
        topics_ctx = (
            "Baseie-se no estilo e no conteúdo das questões de exemplo do professor."
            if language == "pt"
            else "Base these on the style and content of the teacher's example questions."
        )
        questions: list[dict[str, Any]] = []
        for difficulty in DIFFICULTIES:
            for qtype in ("mc", "short"):
                n = plan.get(qtype, {}).get(difficulty, 0)
                if n:
                    questions += question_author.generate_batch(
                        topics_context=topics_ctx,
                        difficulty=difficulty,
                        qtype=qtype,
                        count=n,
                        language=language,
                        seed_examples=seed_examples,
                    )
        usage = token_logger.summarize(run_id)
    finally:
        token_logger.end_run()

    return {
        "run_id": run_id,
        "concepts": [],
        "questions": questions,
        "num_questions": len(questions),
        "usage": usage,
    }
