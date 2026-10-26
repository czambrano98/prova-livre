"""
Render assembled exams and answer keys to printable PDF (Letter size).

Uses fpdf2 with the bundled DejaVu font so Portuguese accents and math symbols
(sigma, epsilon, squared, etc.) render correctly. An optional school header can
be printed at the top of every page for consistency.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos

_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_LETTERS = "ABCDEFGH"

_INK = (31, 45, 51)
_NAVY = (22, 48, 58)
_TEAL = (47, 143, 132)
_MUTED = (86, 104, 114)
_OK = (29, 107, 79)
_DIFF_RGB = {"easy": (58, 140, 126), "medium": (192, 138, 62), "hard": (187, 90, 99)}
_DIFF_LABEL = {
    "pt": {"easy": "fácil", "medium": "média", "hard": "difícil"},
    "en": {"easy": "easy", "medium": "medium", "hard": "hard"},
}


def _new_pdf() -> FPDF:
    pdf = FPDF(format="Letter", unit="mm")
    pdf.add_font("DejaVu", "", str(_FONT_DIR / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(_FONT_DIR / "DejaVuSans-Bold.ttf"))
    pdf.set_margins(18, 16, 18)
    pdf.set_auto_page_break(True, margin=18)
    return pdf


def _width(pdf: FPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin


def _rule(pdf: FPDF, color=_TEAL, h=1.0) -> None:
    pdf.set_draw_color(*color)
    pdf.set_line_width(h)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(3)


def _page_header(pdf: FPDF, exam_name: str, school: str) -> None:
    if school:
        pdf.set_font("DejaVu", "B", 12)
        pdf.set_text_color(*_NAVY)
        pdf.multi_cell(_width(pdf), 6, school, align="C")
        pdf.ln(1)
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_text_color(*_TEAL)
    pdf.cell(0, 5, "ProvaLivre", ln=1)
    pdf.set_font("DejaVu", "B", 16)
    pdf.set_text_color(*_NAVY)
    pdf.multi_cell(_width(pdf), 8, exam_name)
    pdf.ln(1)
    _rule(pdf)


def _answer_lines(pdf: FPDF, n: int = 2) -> None:
    pdf.set_draw_color(190, 198, 203)
    pdf.set_line_width(0.2)
    for _ in range(n):
        pdf.ln(7)
        y = pdf.get_y()
        pdf.line(pdf.l_margin + 2, y, pdf.w - pdf.r_margin - 2, y)
    pdf.ln(5)


def render_exams_pdf(exams: list[dict[str, Any]], *, exam_name: str,
                     lang: str = "pt", school: str = "") -> bytes:
    labels = _DIFF_LABEL.get(lang, _DIFF_LABEL["pt"])
    name_l = "Nome:" if lang == "pt" else "Name:"
    student_l = "Aluno" if lang == "pt" else "Student"
    date_l = "Data:" if lang == "pt" else "Date:"
    legend_l = "Dificuldade:" if lang == "pt" else "Difficulty:"

    pdf = _new_pdf()
    for ex in exams:
        pdf.add_page()
        _page_header(pdf, exam_name, school)

        pdf.set_font("DejaVu", "", 11)
        pdf.set_text_color(*_MUTED)
        pdf.cell(0, 6, f"{student_l}: {ex['student_id']}", ln=1)
        pdf.set_text_color(*_INK)
        pdf.cell(0, 7, f"{name_l} ______________________________    {date_l} ____/____/______", ln=1)

        # legend
        pdf.ln(1)
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(*_MUTED)
        pdf.cell(22, 5, legend_l)
        for d in ("easy", "medium", "hard"):
            pdf.set_text_color(*_DIFF_RGB[d])
            pdf.cell(pdf.get_string_width(labels[d]) + 8, 5, "● " + labels[d])
        pdf.ln(8)

        for it in ex["items"]:
            d = it["difficulty"]
            # difficulty tag, right aligned on its own line
            pdf.set_x(pdf.l_margin)
            pdf.set_font("DejaVu", "B", 9)
            pdf.set_text_color(*_DIFF_RGB[d])
            pdf.cell(_width(pdf), 5, labels[d], align="R",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            # question text
            pdf.set_x(pdf.l_margin)
            pdf.set_font("DejaVu", "", 11)
            pdf.set_text_color(*_INK)
            pdf.multi_cell(_width(pdf), 6, f"{it['number']}.  {it['question_text']}",
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            if it["type"] == "mc":
                pdf.set_font("DejaVu", "", 11)
                for i, opt in enumerate(it["options"]):
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(_width(pdf), 6, f"      ({_LETTERS[i]})  {opt}",
                                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(2)
            elif it["type"] == "short":
                _answer_lines(pdf, 2)
            else:  # math
                _answer_lines(pdf, 3)
            pdf.ln(2)

    return bytes(pdf.output())


def _key_line(pdf: FPDF, ak: dict[str, Any]) -> None:
    n = ak["number"]
    w = _width(pdf)
    if ak["type"] == "mc":
        pdf.set_font("DejaVu", "B", 11)
        pdf.set_text_color(*_OK)
        pdf.multi_cell(w, 6, f"{n}.  ({ak['correct_letter']})  {ak['correct_answer']}")
    elif ak["type"] == "short":
        pdf.set_font("DejaVu", "", 11)
        pdf.set_text_color(*_INK)
        pdf.multi_cell(w, 6, f"{n}.  {ak['model_answer']}")
    else:
        units = f" {ak['answer_units']}" if ak.get("answer_units") else ""
        vals = ", ".join(f"{k}={v}" for k, v in ak.get("values", {}).items())
        pdf.set_font("DejaVu", "B", 11)
        pdf.set_text_color(*_OK)
        pdf.multi_cell(w, 6, f"{n}.  {ak['answer']}{units}   ({vals})")


def render_keys_pdf(exams: list[dict[str, Any]], *, exam_name: str,
                    lang: str = "pt", school: str = "") -> bytes:
    kw = "Gabaritos" if lang == "pt" else "Answer Keys"
    student_l = "Aluno" if lang == "pt" else "Student"

    pdf = _new_pdf()
    pdf.add_page()
    _page_header(pdf, f"{exam_name} ({kw})", school)
    for ex in exams:
        pdf.set_font("DejaVu", "B", 12)
        pdf.set_text_color(*_NAVY)
        pdf.ln(2)
        pdf.cell(0, 7, f"{student_l}: {ex['student_id']}", ln=1)
        pdf.set_draw_color(220, 226, 228)
        pdf.set_line_width(0.2)
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(2)
        for ak in ex["answer_key"]:
            _key_line(pdf, ak)
        pdf.ln(3)
    return bytes(pdf.output())
