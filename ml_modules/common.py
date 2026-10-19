"""Loader partagé ; pas de chargement au démarrage et aucun modèle dans Git.

Ne chargez jamais un .joblib d'une source non fiable. joblib/pickle peut exécuter du code.
"""
from functools import lru_cache
from pathlib import Path

MODEL_ROOT = Path(__file__).resolve().parent.parent / 'ml_models'

class ModelNotReady(RuntimeError):
    pass

def model_path(slug):
    if slug not in {'income', 'occupation', 'age', 'hours', 'education', 'workclass'}:
        raise ValueError('Module inconnu')
    return MODEL_ROOT / slug / 'pipeline.joblib'

def model_installed(slug):
    return model_path(slug).is_file()

@lru_cache(maxsize=6)
def load_pipeline(slug):
    path = model_path(slug)
    if not path.is_file():
        raise ModelNotReady('Le modèle de ce module n’est pas encore connecté. Ajoutez ml_models/' + slug + '/pipeline.joblib.')
    try:
        import joblib
    except ImportError as exc:
        raise ModelNotReady('Installez joblib ainsi que les dépendances du pipeline dans votre environnement.') from exc
    return joblib.load(path)  # uniquement fichiers de l'équipe approuvés


def sample_frame(profile, mapping=None):
    try:
        import pandas as pd
    except ImportError as exc:
        raise ModelNotReady('Installer pandas pour utiliser les modèles ML.') from exc
    mapping = mapping or {}
    # Une seule ligne contenant les features BRUTES utilisées au fit du pipeline.
    return pd.DataFrame([{mapping.get(key, key): float(val) if hasattr(val, 'as_tuple') else val for key, val in profile.items()}])


def predict_generic(slug, profile, *, mapping=None, kind='classification', labels=None):
    """Adaptateur de démarrage pour pipelines scikit-learn compatibles.

    Vérifier les FEATURES, le prétraitement, les classes et la sortie dans chaque adapter.
    """
    pipeline = load_pipeline(slug)
    x = sample_frame(profile, mapping)
    try:
        raw = pipeline.predict(x)[0]
    except Exception as exc:
        raise ModelNotReady('Pipeline incompatible avec les entrées du formulaire : ajustez ml_modules/' + slug + '/adapter.py et portal/catalog.py.') from exc
    if hasattr(raw, 'item'): raw = raw.item()
    if kind == 'regression':
        return {'label': f'{float(raw):.1f}', 'value': float(raw), 'unit': 'ans' if slug == 'age' else 'heures / semaine', 'note': 'Estimation statistique à vérifier.'}
    if kind == 'clustering':
        return {'label': f'Segment {raw}', 'segment': str(raw), 'note': 'Segment descriptif, non prédiction de métier.'}
    label = labels.get(str(raw), str(raw)) if labels else str(raw)
    return {'label': label, 'note': 'Estimation statistique non décisionnelle.'}
