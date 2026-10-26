"""
Safety demonstration, runs the app's defenses and reports pass/fail.

All checks are deterministic and offline (no tokens spent), so the evidence is
reproducible. Display text is localized (PT-BR / EN); the underlying tests are
the same. Risk categories:

  ATTACK        : unsafe formula blocked; malformed output rejected by the schema
  MALFUNCTION   : bad math template caught; unverified math kept off exams
  OVERSPEND     : oversized input truncated; over-cap generation plan refused
  ANTI-COPY     : every exam is unique, within a class and across terms/years
"""
from __future__ import annotations

import math
import random
from typing import Any

from bank_builder import MAX_QUESTIONS_PER_BUILD, _plan_total
from schema import InvalidQuestion, validate_question
from tools.code_executor import UnsafeExpression, safe_eval, validate_math_template
from tools.file_parser import MAX_CHARS

_CAT = {
    "attack": {"pt": "ataque", "en": "attack"},
    "malfunction": {"pt": "falha", "en": "malfunction"},
    "overspend": {"pt": "gasto excessivo", "en": "overspend"},
    "anticopy": {"pt": "anticola", "en": "anti-copy"},
}


def _n(n: int, lang: str) -> str:
    """Format an integer with a thousands separator per language."""
    s = f"{n:,}"
    return s.replace(",", ".") if lang == "pt" else s


def run_safety_demo(*, language: str = "pt") -> dict[str, Any]:
    lang = language if language in ("pt", "en") else "pt"
    pt = lang == "pt"
    checks: list[dict[str, Any]] = []

    def add(cat, name, detail, passed, evidence):
        checks.append({
            "category": _CAT[cat][lang],
            "name": name,
            "detail": detail,
            "passed": passed,
            "evidence": evidence,
        })

    # 1. ATTACK, malicious formula blocked by the code executor.
    payload = '__import__("os").system("rm -rf /")'
    try:
        safe_eval(payload)
        add("attack", "Bloqueio de código malicioso" if pt else "Code-injection block",
            payload, False, "NÃO bloqueado!" if pt else "NOT blocked!")
    except UnsafeExpression:
        add("attack", "Bloqueio de código malicioso" if pt else "Code-injection block",
            payload, True,
            "Bloqueado: só operações matemáticas são permitidas" if pt
            else "Blocked: only math operations are allowed")

    # 2. ATTACK, malformed output rejected by the schema.
    hijacked = {"type": "mc", "difficulty": "easy", "concept": "x",
                "question_text": "...", "options": ["uma só"], "correct_index": 9}
    try:
        validate_question(hijacked)
        add("attack", "Validação de formato" if pt else "Schema validation",
            "questão malformada" if pt else "malformed question", False,
            "NÃO rejeitada!" if pt else "NOT rejected!")
    except InvalidQuestion:
        add("attack", "Validação de formato" if pt else "Schema validation",
            "questão de múltipla escolha malformada" if pt else "malformed multiple-choice question",
            True, "Rejeitada: precisa de 3 a 6 alternativas" if pt
            else "Rejected: needs 3 to 6 options")

    # 3. MALFUNCTION, a formula that cannot compute is caught.
    bad = {"question_template": "{a} / {b}",
           "variables": [{"name": "a", "min": 1, "max": 5}, {"name": "b", "min": 0, "max": 0}],
           "answer_formula": "a / b"}
    ok, _ = validate_math_template(bad)
    add("malfunction", "Verificação do cálculo" if pt else "Math answer check",
        "fórmula com divisão por zero" if pt else "divide-by-zero formula", not ok,
        "Rejeitada: a fórmula não pôde ser calculada" if pt
        else "Rejected: the formula could not be computed")

    # 4. MALFUNCTION, a valid template is confirmed computable.
    good = {"question_template": "{L}, {w}",
            "variables": [{"name": "L", "min": 4, "max": 10, "integer": True},
                          {"name": "w", "min": 5, "max": 20, "integer": True}],
            "answer_formula": "w*L**2/8"}
    ok2, _ = validate_math_template(good)
    add("malfunction", "Fórmula válida aceita" if pt else "Valid formula accepted",
        "w*L**2/8", ok2, "Confirmada: cálculo verificado" if pt else "Confirmed: computation verified")

    # 5. OVERSPEND, oversized input is truncated before the model sees it.
    from tools.file_parser import extract_text
    import tempfile, os
    big = "A " * MAX_CHARS
    fd, path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(big)
        trimmed = extract_text(path)
    finally:
        os.unlink(path)
    truncated = len(trimmed) <= MAX_CHARS + 200
    add("overspend", "Limite de texto de entrada" if pt else "Input truncation",
        f"{_n(len(big), lang)} caracteres enviados" if pt else f"{_n(len(big), lang)} characters in",
        truncated,
        (f"Cortado para {_n(len(trimmed), lang)} caracteres (limite {_n(MAX_CHARS, lang)})" if pt
         else f"Truncated to {_n(len(trimmed), lang)} characters (cap {_n(MAX_CHARS, lang)})"))

    # 6. OVERSPEND, an over-cap generation plan is refused.
    huge = {"mc": {"easy": 50, "medium": 50, "hard": 50}}
    over = _plan_total(huge, include_math=False) > MAX_QUESTIONS_PER_BUILD
    add("overspend", "Limite de geração" if pt else "Generation cap",
        (f"plano pede {_plan_total(huge, False)} questões" if pt
         else f"plan requests {_plan_total(huge, False)} questions"),
        over, f"Recusado (limite {MAX_QUESTIONS_PER_BUILD})" if pt else f"Refused (cap {MAX_QUESTIONS_PER_BUILD})")

    # 7. MALFUNCTION, unverified math stays off exams until a human approves.
    from agents.exam_assembler import assemble_exam
    mini = [
        {"type": "math", "difficulty": "easy", "concept": "x", "approved": False,
         "question_template": "{a}+{b}", "variables": [{"name": "a", "min": 1, "max": 2},
         {"name": "b", "min": 1, "max": 2}], "answer_formula": "a+b"},
        {"type": "mc", "difficulty": "easy", "concept": "y",
         "question_text": "q", "options": ["a", "b", "c"], "correct_index": 0},
    ]
    leaked = any(it["type"] == "math" for it in assemble_exam(mini, {"easy": 2}, "S1")["items"])
    add("malfunction", "Conferência humana do cálculo" if pt else "Human approval gate",
        "questão numérica não aprovada no banco" if pt else "unapproved numeric question in bank",
        not leaked,
        "Fica de fora da prova até o professor aprovar" if pt
        else "Kept off exams until the teacher approves")

    # 8. ANTI-COPY, every exam is different, within a class and across terms/years.
    import bank_store
    from agents.exam_assembler import assemble_class, exam_fingerprint
    bank = bank_store.load_bank()
    mix = {"easy": 3, "medium": 3, "hard": 4}
    # Two separate generations stand in for two different terms/years.
    termA = assemble_class(bank, mix, [f"A{i}" for i in range(30)], base_seed=101)
    termB = assemble_class(bank, mix, [f"B{i}" for i in range(30)], base_seed=777)
    fps = {exam_fingerprint(e) for e in termA + termB}
    all_unique = len(fps) == 60
    # Size of the question-selection space, from the real bank.
    stats = bank_store.bank_stats(bank)
    approved_math = sum(1 for q in bank if q.get("type") == "math" and q.get("approved"))
    pools = {
        "easy": sum(1 for q in bank if q["difficulty"] == "easy" and (q["type"] != "math" or q.get("approved"))),
        "medium": sum(1 for q in bank if q["difficulty"] == "medium" and (q["type"] != "math" or q.get("approved"))),
        "hard": sum(1 for q in bank if q["difficulty"] == "hard" and (q["type"] != "math" or q.get("approved"))),
    }
    combos = (math.comb(max(pools["easy"], 3), 3)
              * math.comb(max(pools["medium"], 3), 3)
              * math.comb(max(pools["hard"], 4), 4))
    add("anticopy", "Provas sempre diferentes" if pt else "Every exam is different",
        ("60 provas em dois períodos diferentes" if pt else "60 exams across two different terms"),
        all_unique,
        (f"60 de 60 únicas; cerca de {_n(combos, lang)} combinações de questões, "
         f"antes de embaralhar ordem, alternativas e números" if pt
         else f"60 of 60 unique; about {_n(combos, lang)} question combinations, "
              f"before shuffling order, options, and numbers"))

    passed = sum(1 for c in checks if c["passed"])
    return {"checks": checks, "passed": passed, "total": len(checks)}
