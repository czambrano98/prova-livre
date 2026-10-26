"""
Persistence for the question bank and uploaded materials.

The bank is a plain JSON file (data/bank.json) so it survives restarts and grows
across terms — exactly what the teacher asked for. Materials are stored under
data/materials/ with a small JSON index.
"""
from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any

_REPO_DIR = Path(__file__).resolve().parent
_DATA_DIR = _REPO_DIR / "data"
_BANK_FILE = _DATA_DIR / "bank.json"
_SEED_BANK_FILE = _DATA_DIR / "sample_bank.json"
_MATERIALS_DIR = _DATA_DIR / "materials"
_MATERIALS_INDEX = _DATA_DIR / "materials.json"
_LOCK = threading.Lock()


# --------------------------------------------------------------------------- #
# Question bank
# --------------------------------------------------------------------------- #
def _ensure_dirs() -> None:
    _DATA_DIR.mkdir(exist_ok=True)
    _MATERIALS_DIR.mkdir(exist_ok=True)


def load_bank() -> list[dict[str, Any]]:
    """Load the bank. If none exists yet, seed from sample_bank.json if present."""
    if _BANK_FILE.exists():
        return json.loads(_BANK_FILE.read_text(encoding="utf-8"))
    if _SEED_BANK_FILE.exists():
        seed = json.loads(_SEED_BANK_FILE.read_text(encoding="utf-8"))
        save_bank(seed)
        return seed
    return []


def save_bank(bank: list[dict[str, Any]]) -> None:
    with _LOCK:
        _ensure_dirs()
        _BANK_FILE.write_text(
            json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def add_questions(questions: list[dict[str, Any]]) -> int:
    """Append validated questions, assigning ids. Returns how many were added."""
    bank = load_bank()
    for q in questions:
        q.setdefault("id", uuid.uuid4().hex[:10])
    bank.extend(questions)
    save_bank(bank)
    return len(questions)


def delete_question(qid: str) -> bool:
    bank = load_bank()
    new = [q for q in bank if q.get("id") != qid]
    changed = len(new) != len(bank)
    if changed:
        save_bank(new)
    return changed


def update_question(qid: str, fields: dict[str, Any]) -> bool:
    bank = load_bank()
    found = False
    for q in bank:
        if q.get("id") == qid:
            q.update(fields)
            found = True
            break
    if found:
        save_bank(bank)
    return found


def clear_bank() -> None:
    save_bank([])


def bank_stats(bank: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Counts by difficulty and type, for the dashboard and for the mix picker."""
    bank = bank if bank is not None else load_bank()
    stats: dict[str, Any] = {
        "total": len(bank),
        "by_difficulty": {"easy": 0, "medium": 0, "hard": 0},
        "by_type": {"mc": 0, "short": 0, "math": 0},
    }
    for q in bank:
        d = q.get("difficulty")
        t = q.get("type")
        if d in stats["by_difficulty"]:
            stats["by_difficulty"][d] += 1
        if t in stats["by_type"]:
            stats["by_type"][t] += 1
    return stats


# --------------------------------------------------------------------------- #
# Materials (lecture files students can download)
# --------------------------------------------------------------------------- #
def _load_materials_index() -> list[dict[str, Any]]:
    if _MATERIALS_INDEX.exists():
        return json.loads(_MATERIALS_INDEX.read_text(encoding="utf-8"))
    return []


def _save_materials_index(index: list[dict[str, Any]]) -> None:
    _ensure_dirs()
    _MATERIALS_INDEX.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def materials_dir() -> Path:
    _ensure_dirs()
    return _MATERIALS_DIR


def list_materials() -> list[dict[str, Any]]:
    return _load_materials_index()


def register_material(stored_name: str, original_name: str, size: int) -> dict[str, Any]:
    index = _load_materials_index()
    entry = {
        "id": uuid.uuid4().hex[:10],
        "stored_name": stored_name,
        "original_name": original_name,
        "size": size,
    }
    index.append(entry)
    _save_materials_index(index)
    return entry


def get_material(mid: str) -> dict[str, Any] | None:
    for m in _load_materials_index():
        if m["id"] == mid:
            return m
    return None
