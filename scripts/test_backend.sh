#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m compileall -q app acquisition main.py tests
pytest -q tests
python check_mvp.py
