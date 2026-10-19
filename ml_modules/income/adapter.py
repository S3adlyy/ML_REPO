"""Module income — propriété du membre associé.

IMPORTANT : branchez le vrai pipeline et vérifiez ses variables exactes.
Le mapping ci-dessous est un exemple de raccordement, pas une garantie de compatibilité.
Ne jamais utiliser la variable cible comme feature.
"""
from ml_modules.common import predict_generic


def predict(profile):
    return predict_generic(
        'income', profile, kind='classification',
        mapping={'hours_per_week': 'hours-per-week', 'capital_gain': 'capital-gain', 'capital_loss': 'capital-loss'}, labels={'<=50K': '≤ 50 000 USD', '>50K': '> 50 000 USD'},
    )
