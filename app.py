"""
ProvaLivre — Flask web app.

Teacher-facing tool for building a question bank from lecture material and
generating a unique, anti-cheating exam for every student. Runs locally:

    python app.py   ->   http://127.0.0.1:5000
"""
from __future__ import annotations

import uuid
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

import bank_store
from i18n import DEFAULT_LANG, LANGUAGES, STRINGS, t
from schema import InvalidQuestion, validate_question

app = Flask(__name__)
app.secret_key = "provalivre-dev-secret"  # local-only app; not a real secret

_REPO_DIR = Path(__file__).resolve().parent
_SAMPLE_FILE = _REPO_DIR / "data" / "sample_slides" / "resistencia_dos_materiais.md"
_EXAMS_OUT = _REPO_DIR / "exams_output"
_PARSE_EXTS = {".pdf", ".pptx", ".txt", ".md"}


# --------------------------------------------------------------------------- #
# Language handling
# --------------------------------------------------------------------------- #
def current_lang() -> str:
    return session.get("lang", DEFAULT_LANG)


@app.context_processor
def inject_globals():
    lang = current_lang()
    return {
        "lang": lang,
        "languages": LANGUAGES,
        "t": lambda key: t(lang, key),
        "stats": bank_store.bank_stats(),
    }


@app.route("/lang/<code>")
def set_lang(code: str):
    if code in LANGUAGES:
        session["lang"] = code
    return redirect(request.referrer or url_for("dashboard"))


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
@app.route("/")
def dashboard():
    return render_template("dashboard.html")


# --------------------------------------------------------------------------- #
# Materials
# --------------------------------------------------------------------------- #
@app.route("/materials")
def materials():
    return render_template("materials.html", materials=bank_store.list_materials())


@app.route("/materials/upload", methods=["POST"])
def materials_upload():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("No file selected.", "error")
        return redirect(url_for("materials"))
    original = file.filename
    stored = f"{uuid.uuid4().hex[:8]}_{secure_filename(original)}"
    dest = bank_store.materials_dir() / stored
    file.save(dest)
    bank_store.register_material(stored, original, dest.stat().st_size)
    flash("File uploaded.", "ok")
    return redirect(url_for("materials"))


@app.route("/materials/download/<mid>")
def materials_download(mid: str):
    m = bank_store.get_material(mid)
    if not m:
        abort(404)
    path = bank_store.materials_dir() / m["stored_name"]
    if not path.exists():
        abort(404)
    return send_file(path, as_attachment=True, download_name=m["original_name"])


# --------------------------------------------------------------------------- #
# Question bank
# --------------------------------------------------------------------------- #
@app.route("/bank")
def bank():
    import random

    from tools.code_executor import instantiate_math_variant

    questions = bank_store.load_bank()
    # For each math question, compute a worked sample so the teacher can verify
    # the AI-written formula before approving it.
    previews: dict[str, str] = {}
    for q in questions:
        if q.get("type") == "math":
            try:
                v = instantiate_math_variant(q, random.Random(7))
                previews[q["id"]] = f'{v["question_text"]}  →  {v["answer"]} {v["answer_units"]}'
            except Exception:
                previews[q["id"]] = "⚠ formula error"
    return render_template("bank.html", questions=questions, previews=previews)


@app.route("/bank/approve/<qid>", methods=["POST"])
def bank_approve(qid: str):
    bank_store.update_question(qid, {"approved": True})
    flash("Math question approved.", "ok")
    return redirect(url_for("bank"))


@app.route("/bank/generate_material", methods=["POST"])
def bank_generate_material():
    # Imported lazily so the rest of the app runs without an API key configured.
    from bank_builder import build_bank_from_material
    from tools.file_parser import extract_text

    lang = current_lang()
    use_sample = request.form.get("use_sample") == "on"
    file = request.files.get("file")

    try:
        if use_sample or not (file and file.filename):
            text = _SAMPLE_FILE.read_text(encoding="utf-8")
        else:
            ext = Path(file.filename).suffix.lower()
            if ext not in _PARSE_EXTS:
                flash(f"Unsupported file type {ext}.", "error")
                return redirect(url_for("bank"))
            tmp = bank_store.materials_dir() / f"tmp_{uuid.uuid4().hex[:8]}{ext}"
            file.save(tmp)
            text = extract_text(tmp)
            tmp.unlink(missing_ok=True)

        result = build_bank_from_material(text, language=lang)
        added = bank_store.add_questions(result["questions"])
        _flash_usage(result, added)
    except Exception as err:  # keep the app from crashing on a bad run
        flash(f"Generation failed: {err}", "error")
    return redirect(url_for("bank"))


@app.route("/bank/generate_seeds", methods=["POST"])
def bank_generate_seeds():
    from bank_builder import build_bank_from_seeds

    lang = current_lang()
    seeds = request.form.get("seeds", "").strip()
    if not seeds:
        flash("Paste at least one example question.", "error")
        return redirect(url_for("bank"))
    try:
        result = build_bank_from_seeds(seeds, language=lang)
        added = bank_store.add_questions(result["questions"])
        _flash_usage(result, added)
    except Exception as err:
        flash(f"Generation failed: {err}", "error")
    return redirect(url_for("bank"))


@app.route("/bank/manual_add", methods=["POST"])
def bank_manual_add():
    lang = current_lang()
    f = request.form
    q = {
        "type": f.get("type"),
        "difficulty": f.get("difficulty"),
        "concept": f.get("concept"),
        "question_text": f.get("question_text"),
        "language": lang,
    }
    if f.get("type") == "mc":
        opts = [f.get(f"opt{i}", "").strip() for i in range(4)]
        q["options"] = [o for o in opts if o]
        try:
            q["correct_index"] = int(f.get("correct_index", 0))
        except ValueError:
            q["correct_index"] = 0
    elif f.get("type") == "short":
        q["answer"] = f.get("answer")
    try:
        clean = validate_question(q)
        bank_store.add_questions([clean])
        flash("Question added.", "ok")
    except InvalidQuestion as err:
        flash(f"Invalid question: {err}", "error")
    return redirect(url_for("bank"))


@app.route("/bank/delete/<qid>", methods=["POST"])
def bank_delete(qid: str):
    bank_store.delete_question(qid)
    flash("Question deleted.", "ok")
    return redirect(url_for("bank"))


def _flash_usage(result: dict, added: int) -> None:
    from tools.token_logger import estimate_cost

    u = result["usage"]
    cost = estimate_cost(u["prompt_tokens"], u["cached_tokens"], u["completion_tokens"])
    flash(
        f"Added {added} questions. "
        f"Tokens — in {u['prompt_tokens']}, cached {u['cached_tokens']}, "
        f"out {u['completion_tokens']}. Est. cost ${cost:.4f}.",
        "ok",
    )


# --------------------------------------------------------------------------- #
# Exam generation
# --------------------------------------------------------------------------- #
@app.route("/exam")
def exam():
    return render_template("exam.html", result=session.pop("exam_result", None))


@app.route("/exam/generate", methods=["POST"])
def exam_generate():
    from agents.exam_assembler import assemble_class, exam_fingerprint
    from exam_render import render_exams_html, render_keys_html

    lang = current_lang()
    f = request.form

    def _int(name, default=0):
        try:
            return max(0, int(f.get(name, default)))
        except ValueError:
            return default

    mix = {"easy": _int("easy", 3), "medium": _int("medium", 3), "hard": _int("hard", 4)}
    n_students = min(_int("students", 5) or 5, 300)  # cap to keep it snappy
    exam_name = f.get("exam_name", "").strip() or ("Prova" if lang == "pt" else "Exam")

    bank = bank_store.load_bank()
    if not bank:
        flash(t(lang, "bank_empty"), "error")
        return redirect(url_for("exam"))

    pending_math = sum(
        1 for q in bank if q.get("type") == "math" and not q.get("approved", False)
    )
    if pending_math:
        flash(f"{pending_math} {t(lang, 'exam_math_excluded')}", "error")

    students = [f"{('Aluno' if lang=='pt' else 'Student')} {i:02d}" for i in range(1, n_students + 1)]
    exams = assemble_class(bank, mix, students, base_seed=uuid.uuid4().int % 100000)

    unique = len({exam_fingerprint(e) for e in exams})
    shortfall = any(e["shortfalls"] for e in exams)

    token = uuid.uuid4().hex[:10]
    _EXAMS_OUT.mkdir(exist_ok=True)
    (_EXAMS_OUT / f"{token}_exams.html").write_text(
        render_exams_html(exams, exam_name=exam_name, lang=lang), encoding="utf-8"
    )
    (_EXAMS_OUT / f"{token}_keys.html").write_text(
        render_keys_html(exams, exam_name=exam_name, lang=lang), encoding="utf-8"
    )

    session["exam_result"] = {
        "token": token,
        "count": len(exams),
        "unique": unique,
        "shortfall": shortfall,
        "exam_name": exam_name,
        "sample": exams[0] if exams else None,
    }
    return redirect(url_for("exam"))


@app.route("/exam/download/<token>/<kind>")
def exam_download(token: str, kind: str):
    if kind not in ("exams", "keys"):
        abort(404)
    safe_token = secure_filename(token)
    path = _EXAMS_OUT / f"{safe_token}_{kind}.html"
    if not path.exists():
        abort(404)
    return send_file(path, as_attachment=True, download_name=f"{kind}.html")


# --------------------------------------------------------------------------- #
# Safety demo
# --------------------------------------------------------------------------- #
@app.route("/safety", methods=["GET", "POST"])
def safety():
    report = None
    if request.method == "POST":
        from safety_demo import run_safety_demo

        report = run_safety_demo(language=current_lang())
    return render_template("safety.html", report=report)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
