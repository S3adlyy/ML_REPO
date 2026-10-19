"""Vérifier le modèle XGBoost directement, SANS avoir besoin de Django.

Commande depuis la racine : python scripts/doctor_model.py
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml_modules.education.adapter import RAW_COLUMNS, predict, read_metadata
from ml_modules.common import model_path, load_pipeline

example = {
    'age': 28, 'hours_per_week': 40,
    'capital_gain': 0, 'capital_loss': 0,
    'workclass': 'Private', 'occupation': 'Adm-clerical', 'income': '<=50K',
}

def main():
    path = model_path('education')
    assert path.is_file(), f'Modèle introuvable: {path}'
    model = load_pipeline('education')
    assert [str(c) for c in model.classes_] == ['0', '1']
    assert set(model.feature_names_in_) == set(RAW_COLUMNS)
    metadata = read_metadata()
    out = predict(example)
    assert out['label'] in ('Niveau supérieur', 'Niveau non supérieur')
    assert 0.0 <= out['probability_superior'] <= 1.0
    assert out['threshold'] == float(metadata['threshold'])
    print('✓ Fichier de modèle chargé :', path.relative_to(ROOT))
    print('✓ Features brutes :', ', '.join(RAW_COLUMNS))
    print('✓ Seuil :', out['threshold'])
    print('✓ Prédiction de test :', json.dumps(out, ensure_ascii=False, indent=2))
    print('✓ Modèle Education opérationnel (hors Django)')

if __name__ == '__main__':
    main()
