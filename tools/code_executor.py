"""
Code executor tool — the engine behind math question variants.

Given a formula (as a string) and a set of variables, it computes the exact
answer. This is what lets us generate "same structure, different numbers"
questions whose answer keys are ALWAYS correct: the model only writes the
template + formula; Python does the arithmetic.

Safety: expressions are validated with the `ast` module before evaluation.
Only numbers, named variables, arithmetic, comparisons, and a whitelist of
math functions are allowed. No imports, attribute access, calls to arbitrary
names, comprehensions, or dunder tricks. This doubles as a safety-section demo:
a malicious formula raises UnsafeExpression instead of executing.
"""
from __future__ import annotations

import ast
import math
import operator
import random
from dataclasses import dataclass
from typing import Any

# --------------------------------------------------------------------------- #
# Whitelist
# --------------------------------------------------------------------------- #
_ALLOWED_FUNCS: dict[str, Any] = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
    "log": math.log, "log10": math.log10, "log2": math.log2, "exp": math.exp,
    "floor": math.floor, "ceil": math.ceil, "fabs": math.fabs, "hypot": math.hypot,
    "radians": math.radians, "degrees": math.degrees, "pow": math.pow,
    "abs": abs, "round": round, "min": min, "max": max,
}
_ALLOWED_CONSTS: dict[str, float] = {"pi": math.pi, "e": math.e, "tau": math.tau}

_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_CMP_OPS = {
    ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt,
    ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne,
}

# Guard against absurd exponents that could hang the process.
_MAX_EXPONENT = 1_000


class UnsafeExpression(ValueError):
    """Raised when a formula contains anything outside the whitelist."""


class EvaluationError(ValueError):
    """Raised when a whitelisted expression fails to compute (e.g. div by zero)."""


def _eval_node(node: ast.AST, variables: dict[str, float]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, variables)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise UnsafeExpression(f"Only numeric constants allowed, got {node.value!r}")

    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        if node.id in _ALLOWED_CONSTS:
            return _ALLOWED_CONSTS[node.id]
        raise UnsafeExpression(f"Unknown name '{node.id}'")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BIN_OPS:
            raise UnsafeExpression(f"Operator {op_type.__name__} not allowed")
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        if op_type is ast.Pow and isinstance(right, (int, float)) and right > _MAX_EXPONENT:
            raise UnsafeExpression("Exponent too large")
        return _BIN_OPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise UnsafeExpression(f"Unary op {op_type.__name__} not allowed")
        return _UNARY_OPS[op_type](_eval_node(node.operand, variables))

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, variables)
        result = True
        for op, comparator in zip(node.ops, node.comparators):
            op_type = type(op)
            if op_type not in _CMP_OPS:
                raise UnsafeExpression(f"Comparison {op_type.__name__} not allowed")
            right = _eval_node(comparator, variables)
            result = result and _CMP_OPS[op_type](left, right)
            left = right
        return result

    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, variables) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        return any(values)

    if isinstance(node, ast.IfExp):  # a if cond else b
        return (
            _eval_node(node.body, variables)
            if _eval_node(node.test, variables)
            else _eval_node(node.orelse, variables)
        )

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise UnsafeExpression("Only direct function calls allowed")
        fname = node.func.id
        if fname not in _ALLOWED_FUNCS:
            raise UnsafeExpression(f"Function '{fname}' not allowed")
        if node.keywords:
            raise UnsafeExpression("Keyword arguments not allowed")
        args = [_eval_node(a, variables) for a in node.args]
        return _ALLOWED_FUNCS[fname](*args)

    raise UnsafeExpression(f"Expression element {type(node).__name__} not allowed")


def safe_eval(expr: str, variables: dict[str, float] | None = None) -> float:
    """Safely evaluate a math expression string with the given variables."""
    variables = variables or {}
    if len(expr) > 500:
        raise UnsafeExpression("Formula too long")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as err:
        raise UnsafeExpression(f"Invalid formula syntax: {err}") from err
    try:
        value = _eval_node(tree, variables)
    except UnsafeExpression:
        raise
    except Exception as err:  # div by zero, domain error, etc.
        raise EvaluationError(f"Formula failed to evaluate: {err}") from err
    return value


# --------------------------------------------------------------------------- #
# Variable sampling + template instantiation
# --------------------------------------------------------------------------- #
@dataclass
class VariableSpec:
    name: str
    min: float
    max: float
    integer: bool = False
    decimals: int = 2

    def sample(self, rng: random.Random) -> float:
        if self.integer:
            return rng.randint(int(self.min), int(self.max))
        return round(rng.uniform(self.min, self.max), self.decimals)


def sample_variables(
    specs: list[dict[str, Any]], rng: random.Random
) -> dict[str, float]:
    """Draw one concrete value per variable spec."""
    values: dict[str, float] = {}
    for raw in specs:
        spec = VariableSpec(
            name=raw["name"],
            min=float(raw["min"]),
            max=float(raw["max"]),
            integer=bool(raw.get("integer", False)),
            decimals=int(raw.get("decimals", 2)),
        )
        values[spec.name] = spec.sample(rng)
    return values


def instantiate_math_variant(
    template: dict[str, Any],
    rng: random.Random,
    *,
    answer_decimals: int = 2,
) -> dict[str, Any]:
    """
    Turn a math template into a concrete question + computed answer.

    Expected template keys:
        question_template : str with {var} placeholders
        variables         : list of variable specs (name, min, max, integer, decimals)
        answer_formula    : expression string using the variable names
        answer_units      : optional str (e.g. "kN", "cm")

    Returns a dict with the filled question text, the sampled values, and the
    exact computed answer. Verified by actually running the formula.
    """
    values = sample_variables(template.get("variables", []), rng)
    answer = safe_eval(template["answer_formula"], values)
    if isinstance(answer, float):
        answer = round(answer, answer_decimals)

    try:
        question_text = template["question_template"].format(**values)
    except (KeyError, IndexError) as err:
        raise EvaluationError(
            f"Question template references an undefined variable: {err}"
        ) from err

    return {
        "question_text": question_text,
        "values": values,
        "answer": answer,
        "answer_units": template.get("answer_units", ""),
    }


def validate_math_template(template: dict[str, Any]) -> tuple[bool, str]:
    """
    Dry-run a math template a few times to confirm it always computes.
    Returns (ok, message). Used by the Math Variant agent to reject bad output
    (agent-malfunction defense).
    """
    required = {"question_template", "variables", "answer_formula"}
    missing = required - set(template)
    if missing:
        return False, f"Missing keys: {sorted(missing)}"
    rng = random.Random(12345)
    try:
        for _ in range(5):
            instantiate_math_variant(template, rng)
    except (UnsafeExpression, EvaluationError) as err:
        return False, str(err)
    return True, "ok"
