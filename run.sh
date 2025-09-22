#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
python run.py
