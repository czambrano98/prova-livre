"""
Render assembled exams to self-contained, printable HTML.

Produces two documents:
  - student exams (one per page, no answers)
  - answer keys (one block per student)
Teachers print to PDF from the browser. No external assets, so files open
anywhere by double-clicking.
"""
from __future__ import annotations

import html
from typing import Any

_LETTERS = "ABCDEFGH"

_CSS = """
body { font-family: Georgia, 'Times New Roman', serif; color: #111; margin: 0; }
.page { padding: 28px 40px; page-break-after: always; }
.page:last-child { page-break-after: auto; }
h1 { font-size: 22px; margin: 0 0 2px; }
.meta { color: #333; font-size: 14px; margin-bottom: 4px; }
.namebar { margin: 12px 0 18px; font-size: 15px; border-bottom: 1px solid #999; padding-bottom: 10px; }
.q { margin: 0 0 16px; font-size: 15px; line-height: 1.5; }
.q .num { font-weight: bold; }
.q .tag { color: #555; font-size: 12px; font-weight: normal; }
.opts { list-style: none; padding-left: 18px; margin: 6px 0; }
.opts li { margin: 3px 0; }
.lines { border-bottom: 1px solid #bbb; height: 20px; margin: 6px 0; }
.key h2 { font-size: 16px; margin: 16px 0 6px; }
.key .item { font-size: 14px; margin: 3px 0; }
.correct { color: #0a6b3b; font-weight: bold; }
"""


def _esc(x: Any) -> str:
    return html.escape(str(x))


def _render_item_student(item: dict[str, Any], labels: dict[str, str]) -> str:
    tag = f'<span class="tag">[{labels.get(item["difficulty"], item["difficulty"])}]</span>'
    head = f'<div class="q"><span class="num">{item["number"]}.</span> {_esc(item["question_text"])} {tag}'
    if item["type"] == "mc":
        opts = "".join(
            f"<li>({_LETTERS[i]}) {_esc(o)}</li>" for i, o in enumerate(item["options"])
        )
        return head + f'<ul class="opts">{opts}</ul></div>'
    if item["type"] == "short":
        return head + '<div class="lines"></div><div class="lines"></div></div>'
    # math -> space to work
    return head + '<div class="lines"></div><div class="lines"></div><div class="lines"></div></div>'


def _render_key_item(ak: dict[str, Any]) -> str:
    n = ak["number"]
    if ak["type"] == "mc":
        return f'<div class="item">{n}. <span class="correct">({ak["correct_letter"]})</span> {_esc(ak["correct_answer"])}</div>'
    if ak["type"] == "short":
        return f'<div class="item">{n}. {_esc(ak["model_answer"])}</div>'
    units = f' {_esc(ak["answer_units"])}' if ak.get("answer_units") else ""
    vals = ", ".join(f"{k}={v}" for k, v in ak.get("values", {}).items())
    return (
        f'<div class="item">{n}. <span class="correct">{_esc(ak["answer"])}{units}</span>'
        f' <span class="tag">({vals})</span></div>'
    )


def render_exams_html(
    exams: list[dict[str, Any]],
    *,
    exam_name: str,
    lang: str = "pt",
) -> str:
    labels = (
        {"easy": "fácil", "medium": "média", "hard": "difícil"}
        if lang == "pt"
        else {"easy": "easy", "medium": "medium", "hard": "hard"}
    )
    name_label = "Nome:" if lang == "pt" else "Name:"
    student_label = "Aluno" if lang == "pt" else "Student"
    date_label = "Data:" if lang == "pt" else "Date:"

    pages = []
    for ex in exams:
        items = "".join(_render_item_student(it, labels) for it in ex["items"])
        pages.append(
            f'<div class="page"><h1>{_esc(exam_name)}</h1>'
            f'<div class="meta">{student_label}: {_esc(ex["student_id"])}</div>'
            f'<div class="namebar">{name_label} ____________________________   {date_label} ______/______/______</div>'
            f"{items}</div>"
        )
    return _document("".join(pages), exam_name)


def render_keys_html(
    exams: list[dict[str, Any]],
    *,
    exam_name: str,
    lang: str = "pt",
) -> str:
    title = (f"{exam_name} — Gabaritos" if lang == "pt" else f"{exam_name} — Answer Keys")
    student_label = "Aluno" if lang == "pt" else "Student"
    blocks = []
    for ex in exams:
        key_items = "".join(_render_key_item(ak) for ak in ex["answer_key"])
        blocks.append(
            f'<div class="key"><h2>{student_label}: {_esc(ex["student_id"])}</h2>{key_items}</div>'
        )
    return _document(f'<div class="page">{"".join(blocks)}</div>', title)


def _document(body: str, title: str) -> str:
    return (
        "<!DOCTYPE html><html lang='pt'><head><meta charset='utf-8'>"
        f"<title>{_esc(title)}</title><style>{_CSS}</style></head>"
        f"<body>{body}</body></html>"
    )
