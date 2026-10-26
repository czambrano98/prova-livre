"""
Token usage logger for the tokenomics report.

Every LLM call appends one JSON line to logs/usage.jsonl with the token counts.
Helpers summarize a run (by label) and the whole log, and estimate cost.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_DIR = Path(__file__).resolve().parent.parent
_LOG_DIR = _REPO_DIR / "logs"
_LOG_FILE = _LOG_DIR / "usage.jsonl"
_LOCK = threading.Lock()

# gpt-6-luna pricing is set by the course Portkey workspace. These per-1M-token
# figures are placeholders used ONLY for cost estimates in the report; the real
# token COUNTS below come straight from the API and are what the rubric grades.
# Override via set_pricing() once the official numbers are confirmed.
PRICING_USD_PER_MTOK = {
    "input": 0.15,
    "cached_input": 0.075,
    "output": 0.60,
}

# A single run can be grouped by a run id so the report can trace "one real run".
_CURRENT_RUN_ID: str | None = None


def set_pricing(input_: float, cached_input: float, output: float) -> None:
    PRICING_USD_PER_MTOK.update(
        input=input_, cached_input=cached_input, output=output
    )


def start_run(run_id: str | None = None) -> str:
    """Begin a named run; subsequent log_usage calls are tagged with it."""
    global _CURRENT_RUN_ID
    _CURRENT_RUN_ID = run_id or f"run-{int(time.time())}"
    return _CURRENT_RUN_ID


def end_run() -> None:
    global _CURRENT_RUN_ID
    _CURRENT_RUN_ID = None


def log_usage(
    *,
    label: str,
    model: str,
    prompt_tokens: int,
    cached_tokens: int,
    completion_tokens: int,
    total_tokens: int,
) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": _CURRENT_RUN_ID,
        "label": label,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "cached_tokens": cached_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }
    with _LOCK:
        _LOG_DIR.mkdir(exist_ok=True)
        with _LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")


def _read_records() -> list[dict[str, Any]]:
    if not _LOG_FILE.exists():
        return []
    out = []
    with _LOG_FILE.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def estimate_cost(
    prompt_tokens: int, cached_tokens: int, completion_tokens: int
) -> float:
    """USD cost estimate. Non-cached input is prompt_tokens minus cached_tokens."""
    non_cached = max(prompt_tokens - cached_tokens, 0)
    return (
        non_cached / 1_000_000 * PRICING_USD_PER_MTOK["input"]
        + cached_tokens / 1_000_000 * PRICING_USD_PER_MTOK["cached_input"]
        + completion_tokens / 1_000_000 * PRICING_USD_PER_MTOK["output"]
    )


def summarize(run_id: str | None = None) -> dict[str, Any]:
    """Totals across the log, or just one run_id if given."""
    records = _read_records()
    if run_id is not None:
        records = [r for r in records if r.get("run_id") == run_id]

    totals = {
        "calls": len(records),
        "prompt_tokens": sum(r["prompt_tokens"] for r in records),
        "cached_tokens": sum(r["cached_tokens"] for r in records),
        "completion_tokens": sum(r["completion_tokens"] for r in records),
        "total_tokens": sum(r["total_tokens"] for r in records),
    }
    totals["cost_usd"] = round(
        estimate_cost(
            totals["prompt_tokens"],
            totals["cached_tokens"],
            totals["completion_tokens"],
        ),
        6,
    )

    by_label: dict[str, dict[str, int]] = {}
    for r in records:
        b = by_label.setdefault(
            r["label"],
            {"calls": 0, "prompt_tokens": 0, "cached_tokens": 0, "completion_tokens": 0},
        )
        b["calls"] += 1
        b["prompt_tokens"] += r["prompt_tokens"]
        b["cached_tokens"] += r["cached_tokens"]
        b["completion_tokens"] += r["completion_tokens"]
    totals["by_label"] = by_label
    return totals
