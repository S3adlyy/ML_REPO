"""Vérifier le modèle XGBoost directement, SANS avoir besoin de Django.

Commande depuis la racine : python scripts/doctor_model.py
"""
import json
from pathlib import Path
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))

from ml_modules.education.adapter import RAW_COLUMNS, predict, read_metadata
from ml_modules.common import model_path, load_pipeline

example = {
    'age': 28, 'hours_per_week': 40,
    'capital_gain': 0, 'capital_loss': 0,
    'workclass': 'Private', 'occupation': 'Adm-clerical', 'income': '<=50K',
}

def check_education():
    from ml_modules.education.adapter import RAW_COLUMNS, predict, read_metadata
    path = model_path('education')
    if not path.is_file():
        print(f'Modèle education non présent localement ({path.name})')
        return False
    model = load_pipeline('education')
    assert [str(c) for c in model.classes_] == ['0', '1']
    assert set(model.feature_names_in_) == set(RAW_COLUMNS)
    metadata = read_metadata()
    out = predict(example)
    assert out['label'] in ('Niveau supérieur', 'Niveau non supérieur')
    assert 0.0 <= out['probability_superior'] <= 1.0
    assert out['threshold'] == float(metadata['threshold'])
    print('✓ Fichier de modèle Education chargé :', path.relative_to(ROOT))
    print('✓ Features brutes :', ', '.join(RAW_COLUMNS))
    print('✓ Seuil :', out['threshold'])
    print('✓ Prédiction de test :', json.dumps(out, ensure_ascii=False, indent=2))
    print('✓ Modèle Education opérationnel (hors Django)')
    return True

def check_has_capital():
    from ml_modules.has_capital.adapter import RAW_COLUMNS, predict, read_metadata
    path = model_path('has_capital')
    if not path.is_file():
        print(f'Modèle has_capital non présent localement ({path.name})')
        return False
    model = load_pipeline('has_capital')
    assert [str(c) for c in model.classes_] == ['0', '1']
    metadata = read_metadata()
    ex = {
        'age': 35, 'education': 'Bachelors', 'workclass': 'Private',
        'occupation': 'Exec-managerial', 'hours_per_week': 45,
        'marital_status': 'Married-civ-spouse', 'relationship': 'Husband',
        'income': '>50K', 'native_us': '1',
    }
    out = predict(ex)
    assert 'label' in out
    assert 0.0 <= out['probability_capital'] <= 1.0
    print('✓ Fichier de modèle has_capital chargé :', path.relative_to(ROOT))
    print('✓ Features brutes :', ', '.join(RAW_COLUMNS))
    print('✓ Seuil :', out['threshold'])
    print('✓ Prédiction de test :', json.dumps(out, ensure_ascii=False, indent=2))
    print('✓ Modèle has_capital opérationnel (hors Django)')
    return True

def main():
    target = sys.argv[1].lower() if len(sys.argv) > 1 else None
    if target == 'has_capital':
        check_has_capital()
    elif target == 'education':
        check_education()
    else:
        # Test available models
        checked = False
        if model_path('has_capital').is_file():
            check_has_capital()
            checked = True
        if model_path('education').is_file():
            check_education()
            checked = True
        if not checked:
            print('Aucun modèle .joblib trouvé localement dans ml_models/has_capital ou ml_models/education.')

if __name__ == '__main__':
    main()

