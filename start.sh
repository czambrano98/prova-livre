#!/usr/bin/env bash
# ProvaLivre - run this to start the app:  bash start.sh
set -e
cd "$(dirname "$0")"

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python

if [ ! -x ".venv/bin/python" ]; then
  echo "Creating the environment..."
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
echo "Installing components..."
python -m pip install --quiet --disable-pip-version-check -r requirements.txt

echo "Opening ProvaLivre in your browser..."
python app.py
