"""
Agent: Solution Writer.

Writes a short step-by-step worked solution for each question, in the question's
language. Solutions are generated once per bank question and cached, so a whole
class of commented answer keys costs no extra tokens.

For numeric questions the model explains the METHOD symbolically (which formula,
what each step does), without inventing numbers. The student's actual numbers and
the exact computed answer come from the exam itself, so the solution stays correct
for every variant.
"""
from __future__ import annotations

from typing import Any

from llm_client import chat_json

_SYSTEM = {
    "pt": (
        "Você é um professor de engenharia civil que escreve resoluções claras e "
        "curtas, em português do Brasil, para os alunos entenderem onde erraram. "
        "Responda apenas com JSON válido."
    ),
    "en": (
        "You are a civil-engineering teacher writing clear, short worked solutions "
        "in English so students understand where they went wrong. Respond with only "
        "valid JSON."
    ),
}

_CHUNK = 8


def _describe(q: dict[str, Any]) -> dict[str, Any]:
    d = {"id": q.get("id"), "type": q["type"], "concept": q.get("concept", "")}
    if q["type"] == "mc":
        d["question"] = q["question_text"]
        d["correct_option"] = q["options"][q["correct_index"]]
    elif q["type"] == "short":
        d["question"] = q["question_text"]
        d["model_answer"] = q["answer"]
    else:  # math
        d["question_template"] = q["question_template"]
        d["answer_formula"] = q["answer_formula"]
        d["answer_units"] = q.get("answer_units", "")
    return d


def generate_solutions(
    questions: list[dict[str, Any]], *, language: str = "pt"
) -> dict[str, str]:
    """Return {question_id: solution_text} for the given bank questions."""
    lang = language if language in _SYSTEM else "pt"
    out: dict[str, str] = {}

    if lang == "pt":
        task = (
            "Para cada questão abaixo, escreva uma resolução passo a passo curta "
            "(2 a 5 passos). Para questões numéricas, explique o método usando a "
            "fórmula fornecida e descreva cada passo, SEM inventar valores (os "
            "números são diferentes para cada aluno). "
            'Responda com {"solutions": [{"id": "...", "solution": "..."}]}.'
        )
    else:
        task = (
            "For each question below, write a short step-by-step solution (2 to 5 "
            "steps). For numeric questions, explain the method using the given "
            "formula and describe each step, WITHOUT inventing values (the numbers "
            "differ per student). "
            'Respond with {"solutions": [{"id": "...", "solution": "..."}]}.'
        )

    import json

    for i in range(0, len(questions), _CHUNK):
        chunk = questions[i : i + _CHUNK]
        payload = json.dumps([_describe(q) for q in chunk], ensure_ascii=False)
        messages = [
            {"role": "system", "content": _SYSTEM[lang]},
            {"role": "user", "content": f"{task}\n\n{payload}"},
        ]
        data, _ = chat_json(messages, label="solution_writer", temperature=0.3)
        sols = data.get("solutions", []) if isinstance(data, dict) else []
        for s in sols:
            if isinstance(s, dict) and s.get("id") and s.get("solution"):
                out[str(s["id"])] = str(s["solution"]).strip()
    return out
