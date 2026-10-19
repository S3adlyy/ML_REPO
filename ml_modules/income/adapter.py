"""Pont entre le formulaire Django et le pipeline Income (XGBoost réglé du notebook).

Entrées du formulaire : age, education, workclass, occupation, relationship,
hours_per_week, capital_gain, capital_loss.
Le pipeline .joblib fait lui-même toute la préparation (log1p du capital,
education -> niveau ordonné, One-Hot, regroupement des modalités rares) puis
XGBoost : AUCUN ré-encodage côté Django.

Le modèle est produit par scripts/train_income.py (fichiers locaux, jamais dans Git).
Artefact trusted-only : joblib.load peut exécuter du code Python arbitraire.
"""
from functools import lru_cache
import json
from pathlib import Path

from ml_modules.common import ModelNotReady, load_pipeline, sample_frame

MODEL_DIR = Path(__file__).resolve().parents[2] / 'ml_models' / 'income'

# Nom du champ Django -> nom de la colonne utilisée à l'entraînement
FIELD_MAPPING = {
    'hours_per_week': 'hours-per-week',
    'capital_gain': 'capital-gain',
    'capital_loss': 'capital-loss',
}
RAW_COLUMNS = [
    'age', 'education', 'workclass', 'occupation', 'relationship',
    'hours-per-week', 'capital-gain', 'capital-loss',
]
REQUIRED_FIELDS = {
    'age', 'education', 'workclass', 'occupation', 'relationship',
    'hours_per_week', 'capital_gain', 'capital_loss',
}


@lru_cache(maxsize=1)
def read_metadata():
    """Lit model_metadata.json (écrit par scripts/train_income.py)."""
    path = MODEL_DIR / 'model_metadata.json'
    if not path.is_file():
        raise ModelNotReady('Fichier model_metadata.json manquant : lancez python scripts/train_income.py.')
    try:
        meta = json.loads(path.read_text(encoding='utf-8'))
        if not 0.0 <= float(meta['threshold']) <= 1.0:
            raise ValueError('Seuil invalide')
        if list(meta['raw_expected_columns']) != RAW_COLUMNS:
            raise ValueError('Colonnes différentes des 8 entrées prévues')
        if set(meta['label_mapping']) != {'0', '1'}:
            raise ValueError('label_mapping doit contenir les clés 0 et 1')
        return meta
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise ModelNotReady('Métadonnées du modèle Income invalides.') from exc


def validate(profile):
    """Contrôles métier, utiles aussi si l'adaptateur est appelé hors formulaire."""
    missing = REQUIRED_FIELDS - set(profile)
    if missing:
        raise ValueError('Champs manquants : ' + ', '.join(sorted(missing)))
    if not 17 <= int(profile['age']) <= 90:
        raise ValueError('Âge attendu entre 17 et 90 ans.')
    if not 1 <= float(profile['hours_per_week']) <= 99:
        raise ValueError('Durée de travail attendue entre 1 et 99 heures.')
    if not 0 <= float(profile['capital_gain']) <= 99999:
        raise ValueError('Gains en capital attendus entre 0 et 99 999 USD.')
    if not 0 <= float(profile['capital_loss']) <= 4356:
        raise ValueError('Pertes en capital attendues entre 0 et 4 356 USD.')


def predict(profile):
    """Retourne un dict sérialisable pour le template commun et l'API JSON."""
    validate(profile)
    meta = read_metadata()
    model = load_pipeline('income')

    x = sample_frame({k: profile[k] for k in REQUIRED_FIELDS}, FIELD_MAPPING)[RAW_COLUMNS]
    if not hasattr(model, 'predict_proba'):
        raise ModelNotReady('Le pipeline Income ne possède pas predict_proba().')
    try:
        classes = [str(c) for c in model.classes_]
        idx = classes.index('1')  # 1 = revenu > 50K
        score = float(model.predict_proba(x)[0, idx])
    except (ValueError, IndexError, AttributeError) as exc:
        raise ModelNotReady('Classes du modèle incompatibles : attendu [0, 1].') from exc
    except Exception as exc:
        raise ModelNotReady('Échec de la prédiction : vérifier les variables et les versions ML.') from exc

    threshold = float(meta['threshold'])
    outcome = '1' if score >= threshold else '0'
    score_txt = 'moins de 1 %' if score < 0.01 else f'{score:.0%}'
    return {
        'label': meta['label_mapping'][outcome],
        'probability': round(score, 4),
        'threshold': threshold,
        'note': (f'Probabilité estimée de gagner plus de 50 000 USD/an : {score_txt} '
                 f'(seuil de décision : {threshold:.0%}). Estimation statistique fondée sur '
                 'le recensement américain de 1994, non décisionnelle.'),
    }
