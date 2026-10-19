"""Vérifier le modèle has_capital directement, SANS avoir besoin de Django.

Commande depuis la racine : python scripts/doctor_has_capital.py
"""
import json
from pathlib import Path
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))

from ml_modules.has_capital.adapter import RAW_COLUMNS, predict, read_metadata
from ml_modules.common import model_path, load_pipeline

example = {
    'age': 35,
    'education': 'Bachelors',
    'workclass': 'Private',
    'occupation': 'Exec-managerial',
    'hours_per_week': 45,
    'marital_status': 'Married-civ-spouse',
    'relationship': 'Husband',
    'income': '>50K',
    'native_us': '1',
}


def main():
    path = model_path('has_capital')
    assert path.is_file(), f'Modèle introuvable: {path}'
    model = load_pipeline('has_capital')
    assert [str(c) for c in model.classes_] == ['0', '1'], f'Classes inattendues: {model.classes_}'
    metadata = read_metadata()
    out = predict(example)
    assert 'label' in out and isinstance(out['label'], str)
    assert 0.0 <= out['probability_capital'] <= 1.0
    assert out['threshold'] == float(metadata['threshold'])
    print('✓ Fichier de modèle chargé :', path.relative_to(ROOT))
    print('✓ Features brutes attendues :', ', '.join(RAW_COLUMNS))
    print('✓ Seuil optimal calibré :', out['threshold'])
    print('✓ Score estimé sur exemple :', out['probability_capital'])
    print('✓ Prédiction de test :', json.dumps(out, ensure_ascii=False, indent=2))
    print('✓ Modèle has_capital 100% opérationnel (hors Django)')


if __name__ == '__main__':
    main()
