"""Pont entre le formulaire Django et le VRAI pipeline Education du livrable Adult.

Entrées du formulaire : age, hours_per_week, capital_gain, capital_loss,
workclass, occupation, income. Le pipeline .joblib effectue lui-même
imputation, log1p, OneHotEncoding puis XGBoost : PAS de ré-encodage Django.

Artefact trusted-only : joblib.load peut exécuter du code Python arbitraire.
"""
from functools import lru_cache
import json
from pathlib import Path

from ml_modules.common import ModelNotReady, load_pipeline, sample_frame

MODEL_DIR = Path(__file__).resolve().parents[2] / 'ml_models' / 'education'
FIELD_MAPPING = {
    'hours_per_week': 'hours-per-week',
    'capital_gain': 'capital-gain',
    'capital_loss': 'capital-loss',
}
RAW_COLUMNS = [
    'age', 'hours-per-week', 'capital-gain', 'capital-loss',
    'workclass', 'occupation', 'income',
]

@lru_cache(maxsize=1)
def read_metadata():
    """Métadonnées tirées de model_metadata.json fourni avec le modèle."""
    path = MODEL_DIR / 'model_metadata.json'
    if not path.is_file():
        raise ModelNotReady('Fichier model_metadata.json manquant dans ml_models/education/.')
    try:
        meta = json.loads(path.read_text(encoding='utf-8'))
        if not 0.0 <= float(meta['threshold']) <= 1.0:
            raise ValueError('Seuil invalide')
        if set(meta['raw_expected_columns']) != set(RAW_COLUMNS):
            raise ValueError('Colonnes différentes des 7 entrées prévues')
        return meta
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise ModelNotReady('Métadonnées du modèle Education invalides.') from exc


def predict(profile):
    """Prédit le niveau à partir d'un profil validé dans Django.

    Retourne un dict sérialisable pour le template commun et l'API JSON.
    """
    meta = read_metadata()
    model = load_pipeline('education')

    # Également utile si l'adaptateur est appelé directement hors formulaire.
    required = {'age', 'hours_per_week', 'capital_gain', 'capital_loss',
                'workclass', 'occupation', 'income'}
    if required - set(profile):
        raise ValueError('Champs manquants : ' + ', '.join(sorted(required - set(profile))))
    if not 17 <= int(profile['age']) <= 90:
        raise ValueError('Âge attendu entre 17 et 90 ans.')
    if not 1 <= float(profile['hours_per_week']) <= 99:
        raise ValueError('Durée de travail attendue entre 1 et 99 heures.')
    for key in ('capital_gain', 'capital_loss'):
        if float(profile[key]) < 0:
            raise ValueError(f'{key} ne peut pas être négatif.')
    if profile['income'] not in ('<=50K', '>50K'):
        raise ValueError('Revenu attendu : <=50K ou >50K (catégories historiques UCI).')

    x = sample_frame(profile, FIELD_MAPPING)
    # Le pipeline s'attend à ces sept colonnes brutes; il produit ses propres features.
    x = x[RAW_COLUMNS]
    if not hasattr(model, 'predict_proba'):
        raise ModelNotReady('Le pipeline Education ne possède pas predict_proba().')
    try:
        classes = [str(label) for label in model.classes_]
        idx = classes.index('1')  # 1 = niveau supérieur dans le pipeline fourni
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
        'probability_superior': round(score, 4),
        'threshold': threshold,
        'note': ('Résultat indicatif uniquement. Faire confirmer le niveau réel '
                 'avant de proposer un parcours de formation.'),
    }
