#!/usr/bin/env bash
# Activate the virtualenv and launch the app.
set -e

cd "$(dirname "$0")"
source venv/bin/activate
python app.py
