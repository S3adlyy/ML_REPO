"""Pont entre le formulaire Django et le pipeline has_capital de Bilal El Eter.

Entrées du formulaire : age, education (ou education_num), workclass,
occupation, hours_per_week, marital_status, relationship, income, native_us.

Le pipeline .joblib effectue lui-même :
- StandardScaler sur age, education-num, hours-per-week
- passthrough sur native_us
- OneHotEncoder sur workclass, marital-status, occupation, relationship, income
- HistGradientBoostingClassifier(class_weight='balanced')
Aucun ré-encodage n'est effectué dans Django.
"""
from functools import lru_cache
import json
from pathlib import Path

from ml_modules.common import ModelNotReady, load_pipeline, sample_frame

MODEL_DIR = Path(__file__).resolve().parents[2] / 'ml_models' / 'has_capital'

RAW_COLUMNS = [
    'age',
    'workclass',
    'education-num',
    'marital-status',
    'occupation',
    'relationship',
    'hours-per-week',
    'income',
    'native_us',
]

EDUCATION_TO_NUM = {
    'Preschool': 1,
    '1st-4th': 2,
    '5th-6th': 3,
    '7th-8th': 4,
    '9th': 5,
    '10th': 6,
    '11th': 7,
    '12th': 8,
    'HS-grad': 9,
    'Some-college': 10,
    'Assoc-voc': 11,
    'Assoc-acdm': 12,
    'Bachelors': 13,
    'Masters': 14,
    'Prof-school': 15,
    'Doctorate': 16,
}


@lru_cache(maxsize=1)
def read_metadata():
    """Lit les métadonnées de ml_models/has_capital/model_metadata.json."""
    path = MODEL_DIR / 'model_metadata.json'
    if not path.is_file():
        raise ModelNotReady('Fichier model_metadata.json manquant dans ml_models/has_capital/.')
    try:
        meta = json.loads(path.read_text(encoding='utf-8'))
        if not 0.0 <= float(meta['threshold']) <= 1.0:
            raise ValueError('Seuil invalide')
        if set(meta['raw_expected_columns']) != set(RAW_COLUMNS):
            raise ValueError('Colonnes différentes des 9 entrées attendues')
        return meta
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise ModelNotReady('Métadonnées du modèle has_capital invalides.') from exc


def normalize_profile(profile: dict) -> dict:
    """Valide et prépare le dictionnaire des variables brutes."""
    # Validation minimale des champs
    required = {'age', 'workclass', 'occupation', 'hours_per_week', 'marital_status', 'relationship', 'income'}
    missing = required - set(profile.keys())
    if missing:
        raise ValueError('Champs manquants : ' + ', '.join(sorted(missing)))

    try:
        age_val = int(profile['age'])
    except (ValueError, TypeError):
        raise ValueError('Âge invalide.')
    if not 17 <= age_val <= 90:
        raise ValueError('Âge attendu entre 17 et 90 ans.')

    try:
        hours_val = float(profile['hours_per_week'])
    except (ValueError, TypeError):
        raise ValueError('Heures travaillées invalides.')
    if not 1 <= hours_val <= 99:
        raise ValueError('Durée de travail attendue entre 1 et 99 heures.')

    # Conversion de l'éducation en education-num
    if 'education-num' in profile:
        edu_num = int(profile['education-num'])
    elif 'education_num' in profile:
        edu_num = int(profile['education_num'])
    elif 'education' in profile:
        edu_str = str(profile['education'])
        if edu_str.isdigit():
            edu_num = int(edu_str)
        else:
            edu_num = EDUCATION_TO_NUM.get(edu_str, 9)
    else:
        edu_num = 9

    if not 1 <= edu_num <= 16:
        raise ValueError('Niveau d’études (années) doit être compris entre 1 et 16.')

    # Conversion de l'origine géographique native_us (1 = États-Unis, 0 = autre)
    raw_native = profile.get('native_us', profile.get('native-country', '1'))
    if str(raw_native) in ('1', 'United-States', 'true', 'True'):
        native_us_val = 1
    else:
        native_us_val = 0

    return {
        'age': age_val,
        'workclass': str(profile['workclass']),
        'education-num': edu_num,
        'marital-status': str(profile['marital_status']),
        'occupation': str(profile['occupation']),
        'relationship': str(profile['relationship']),
        'hours-per-week': hours_val,
        'income': str(profile['income']),
        'native_us': native_us_val,
    }


def predict(profile: dict) -> dict:
    """Point d'entrée principal appelé par Django et l'API JSON."""
    meta = read_metadata()
    model = load_pipeline('has_capital')

    norm_profile = normalize_profile(profile)
    x = sample_frame(norm_profile)
    x = x[RAW_COLUMNS]

    if not hasattr(model, 'predict_proba'):
        raise ModelNotReady('Le pipeline has_capital ne possède pas de méthode predict_proba().')

    try:
        classes = [str(c) for c in model.classes_]
        idx = classes.index('1')  # 1 = possède du capital
        score = float(model.predict_proba(x)[0, idx])
    except (ValueError, IndexError, AttributeError) as exc:
        raise ModelNotReady('Classes du modèle incompatibles : attendu [0, 1].') from exc
    except Exception as exc:
        raise ModelNotReady('Échec de la prédiction : vérifier les features et versions ML.') from exc

    threshold = float(meta['threshold'])
    outcome = '1' if score >= threshold else '0'
    label = meta['label_mapping'][outcome]

    return {
        'label': label,
        'probability_capital': round(score, 4),
        'probability_superior': round(score, 4),
        'threshold': threshold,
        'has_capital': outcome == '1',
        'note': (
            'Estimation indicative basée sur le profil socio-professionnel. '
            'Modèle calibré au seuil optimal (rappel 50 %, lift x2.9 sur le 1er décile), '
            'sans utilisation des variables de capital réelles pour éviter toute fuite.'
        ),
    }
