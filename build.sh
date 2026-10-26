#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r requirements.txt
python scripts/fetch_models.py
python manage.py collectstatic --noinput
python scripts/smoke_models.py
