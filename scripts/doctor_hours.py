"""Vérifier le modèle hours SANS Django. Depuis la racine : python scripts/doctor_hours.py"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml_modules.common import model_path, load_pipeline
from ml_modules.hours.adapter import predict

path = model_path('hours')
if not path.is_file():
    sys.exit(f'Modèle hours absent : copiez modele_temps_partiel.joblib vers {path}')
bundle = load_pipeline('hours')
print('Versions utilisées à l’export :', bundle.get('versions'))
print('Colonnes :', len(bundle['colonnes']), '| seuil :', bundle['seuil'])
example = json.loads((ROOT / 'ml_models' / 'hours' / 'exemple_profil.json').read_text(encoding='utf-8'))
print(json.dumps(predict(example), ensure_ascii=False, indent=2))
print('✓ Modèle hours opérationnel (hors Django)')
