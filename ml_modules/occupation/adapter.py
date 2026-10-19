"""Module occupation — propriété du membre associé.

IMPORTANT : branchez le vrai pipeline et vérifiez ses variables exactes.
Le mapping ci-dessous est un exemple de raccordement, pas une garantie de compatibilité.
Ne jamais utiliser la variable cible comme feature.
"""
from ml_modules.common import predict_generic


def predict(profile):
    return predict_generic(
        'occupation', profile, kind='clustering',
        mapping={'hours_per_week': 'hours-per-week', 'marital_status': 'marital-status'}, labels=None,
    )
