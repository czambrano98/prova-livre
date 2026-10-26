# ProvaLivre — Personalized Anti-Cheating Exams for Public Schools

ProvaLivre helps an underfunded public high-school teacher build a reusable
**question bank** from their own lecture material and generate a **different exam
for every student** — same difficulty, different questions and numbers — to make
copying between students (and across terms) nearly impossible.

Built for MGT 409. Bilingual (Português-BR / English). Runs locally.

---

## Quick start (under 10 minutes)

**Requirements:** Python 3.10+.

```bash
# 1. Clone and enter the folder
cd "Final Project"

# 2. Create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key (see "API keys" below)
#    copy .env.example to .env and paste your PORTKEY_API_KEY

# 5. Run
python app.py
```

Open **http://127.0.0.1:5000** in a browser.

> The app ships with a **sample question bank** (Portuguese civil-engineering),
> so you can generate exams and see the safety demo **without an API key**.
> An API key is only needed to *generate new questions* from material.

---

## API keys

The app looks for a `.env` file in **two places, in this order**:

1. this repo folder (`Final Project/.env`)
2. one folder above it (`../.env`)  ← teaching staff place their key here

The app accepts **any one** of three keys (checked in this order), so Portkey,
OpenAI, or Claude all work:

```
PORTKEY_API_KEY=your_key_here      # course key, gpt-6-luna via Portkey (used by staff)
OPENAI_API_KEY=your_key_here       # your own OpenAI model (default gpt-4o-mini)
ANTHROPIC_API_KEY=your_key_here    # your own Claude model (default claude-opus-5-5)
LLM_MODEL=claude-haiku-5-5         # optional: override the model (e.g. cheapest Claude)
```

The first key present wins, so teaching staff with `PORTKEY_API_KEY` always get the
course model. Copy `.env.example` to `.env` and fill in one key. **Never commit your
real `.env`.**

To test the staff setup: move your `.env` up one folder and confirm the app
still runs.

---

## How to use

1. **Question Bank** → *Generate from material*: upload a lecture PDF/PPTX/text
   (or tick "use sample material"). The agents extract concepts and write easy,
   medium, and hard questions (multiple-choice, short-answer, and parameterized
   numeric). You can also *expand from a few example questions* or *add questions
   manually*. The bank is saved and grows across terms.
2. **Generate Exams**: choose the difficulty mix (e.g. 3 easy / 3 medium / 4 hard)
   and the number of students. Each student gets a unique exam with shuffled
   questions, shuffled multiple-choice options, and freshly computed numbers for
   math questions. Download the **student exams** and the **answer keys** as
   printable HTML.
3. **Materials**: upload lecture files for students to download.
4. **Safety**: run the built-in defense demonstration.

---

## Test data vs. full data

- **Test data (default):** `data/sample_slides/` holds a small synthetic lecture
  file, and `data/sample_bank.json` seeds a ready-to-use bank on first run.
- **Full data:** upload your own lecture files on the *Question Bank* page to
  generate a real bank. To reset to the seed bank, delete `data/bank.json` and
  restart (it will re-seed from `data/sample_bank.json`).

---

## How it works (agents)

| Agent | Job | Tool |
|---|---|---|
| Concept Extractor | Pull teachable concepts from lecture text | File parser (PDF/PPTX/text) |
| Question Author | Write MC + short-answer questions per difficulty | — |
| Math Variant Builder | Write parameterized numeric templates | **Code executor** (verifies every answer) |
| Exam Assembler | Build each student's unique exam + key | — (deterministic, no tokens) |

The model only *writes* math templates; Python *computes* the answers, so answer
keys are always correct. Because assembly is deterministic, generating a whole
class — or reusing the bank for years — costs no extra tokens.

Model: **gpt-6-luna** via Portkey.

---

## Project layout

```
app.py              Flask app + routes
llm_client.py       Portkey/gpt-6-luna client + token logging
bank_builder.py     Orchestrates the agent pipeline
bank_store.py       Question bank + materials persistence
schema.py           Question validation (a safety layer)
exam_render.py      Printable exam/answer-key HTML
safety_demo.py      Reproducible defense demonstration
i18n.py             Português / English strings
agents/             concept_extractor, question_author, math_variant, exam_assembler
tools/              file_parser, code_executor, token_logger
templates/ static/  UI
data/               sample material + seed bank (test data)
```
