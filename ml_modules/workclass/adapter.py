"""Module workclass : prédiction de la catégorie professionnelle (5 classes).

Le fichier ml_models/workclass/pipeline.joblib est un dictionnaire
(pipeline, input_columns, classes, versions) produit par le notebook.
Il reste local et n'est jamais commité.
"""
import sys

from ml_modules.common import ModelNotReady, model_installed, model_path
from ml_modules.workclass import workclass_features

# Le pickle référence le module sous le nom top-level « workclass_features ».
sys.modules.setdefault('workclass_features', workclass_features)

_ARTEFACT = None

EDUCATION_NUM = {
    'Preschool': 1, '1st-4th': 2, '5th-6th': 3, '7th-8th': 4, '9th': 5, '10th': 6,
    '11th': 7, '12th': 8, 'HS-grad': 9, 'Some-college': 10, 'Assoc-voc': 11,
    'Assoc-acdm': 12, 'Bachelors': 13, 'Masters': 14, 'Prof-school': 15, 'Doctorate': 16,
}


def _load():
    global _ARTEFACT
    if _ARTEFACT is None:
        if not model_installed('workclass'):
            raise ModelNotReady(
                'Le modèle de ce module n’est pas encore connecté. '
                'Ajoutez ml_models/workclass/pipeline.joblib.'
            )
        try:
            import joblib
        except ImportError as exc:
            raise ModelNotReady('Installez joblib et les dépendances du pipeline.') from exc
        source = model_path('workclass')
        streamed = source.with_name('pipeline-streamed.joblib')
        artifact = joblib.load(streamed if streamed.is_file() else source)
        if streamed.is_file():
            from .streaming import source_digest
            if artifact.get('source_sha256') != source_digest(source):
                raise ModelNotReady('Reconstruisez le modèle progressif après une mise à jour du modèle original.')
        _ARTEFACT = artifact
    return _ARTEFACT


def predict(profile):
    art = _load()
    try:
        import pandas as pd
    except ImportError as exc:
        raise ModelNotReady('Installer pandas pour utiliser les modèles ML.') from exc

    # Noms du formulaire (hours_per_week) -> noms du pipeline (hours-per-week)
    data = {}
    for key, val in profile.items():
        if hasattr(val, 'as_tuple'):  # Decimal -> float
            val = float(val)
        data[key.replace('_', '-')] = val

    # education-num est déduit de education (absent du formulaire)
    data['education-num'] = EDUCATION_NUM.get(data.get('education'))

    columns = art['input_columns']
    missing = [c for c in columns if c not in data]
    if missing:
        raise ModelNotReady('Champs manquants dans le formulaire : ' + ', '.join(missing))

    row = pd.DataFrame([{c: data[c] for c in columns}])
    try:
        pipe = art['pipeline']
        proba = pipe.predict_proba(row)[0]
    except Exception as exc:
        raise ModelNotReady(
            'Pipeline incompatible avec les entrées du formulaire : '
            'vérifiez ml_modules/workclass/adapter.py et portal/catalog.py.'
        ) from exc

    ranked = sorted(zip(pipe.classes_, proba), key=lambda kv: -kv[1])
    return {
        'label': str(ranked[0][0]),
        'probabilities': {str(c): round(float(p), 4) for c, p in ranked},
        'note': 'Estimation statistique non décisionnelle (Random Forest, 5 classes).',
    }
