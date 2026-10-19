#!/usr/bin/env bash
# Démarrage local macOS/Linux. Nécessite Python 3.13 et l'accès réseau au premier lancement.
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v python3.13 >/dev/null 2>&1; then
  echo 'Erreur: installer Python 3.13 avant de continuer (python3.13 introuvable).' >&2
  exit 1
fi
if [ ! -d .venv ]; then
  python3.13 -m venv .venv
fi
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/doctor_model.py
python manage.py check
python manage.py migrate
python manage.py test
exec python manage.py runserver
