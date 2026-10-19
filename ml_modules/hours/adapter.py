"""Pont entre le formulaire Django et le modèle « temps partiel » (module hours, Bessem).

Le modèle est un XGBClassifier (cible : hours-per-week <= 34 h => temps partiel).
Le fichier ml_models/hours/pipeline.joblib est un DICTIONNAIRE exporté depuis le
notebook, avec les clés : modele, scaler, colonnes, continues, seuil, categories,
metriques, taux_base, versions.

Ce n'est PAS un Pipeline sklearn : l'adaptateur refait donc exactement le
prétraitement du notebook (log1p, has_capital, One-Hot drop_first, StandardScaler).

Artefact trusted-only : joblib.load peut exécuter du code Python arbitraire.
"""
import math

from ml_modules.common import ModelNotReady, load_pipeline

# Niveau d'études -> education-num (table UCI Adult)
EDUCATION_TO_NUM = {
    'Preschool': 1, '1st-4th': 2, '5th-6th': 3, '7th-8th': 4, '9th': 5,
    '10th': 6, '11th': 7, '12th': 8, 'HS-grad': 9, 'Some-college': 10,
    'Assoc-voc': 11, 'Assoc-acdm': 12, 'Bachelors': 13, 'Masters': 14,
    'Prof-school': 15, 'Doctorate': 16,
}
CATEGORICAL = ('workclass', 'marital-status', 'occupation')
REQUIRED_KEYS = ('modele', 'scaler', 'colonnes', 'continues', 'seuil', 'categories')
LABEL_PART_TIME = 'Temps partiel probable (34 h/semaine ou moins)'
LABEL_FULL_TIME = 'Temps plein probable (plus de 34 h/semaine)'

# Niveaux de priorité de contact. Repères mesurés sur le jeu de test (9 758 personnes,
# 17 % de temps partiels en moyenne) : à recalculer si le modèle est ré-entraîné.
HIGH_PROBA = 0.50
TIERS = {
    'high': ('Priorité élevée : temps partiel très probable', 67),
    'medium': ('Priorité moyenne : temps partiel possible', 35),
    'low': ('Priorité faible : temps plein probable', 9),
}
# Variables du formulaire -> colonnes du modèle qui en dérivent
GROUPS = {
    'age': ('age',),
    'education-num': ('education-num',),
    'workclass': ('workclass_',),
    'marital-status': ('marital-status_',),
    'occupation': ('occupation_',),
    'capital': ('log_capital_gain', 'log_capital_loss', 'has_capital'),
    'native_us': ('native_us',),
}
FACTOR_NAMES = {
    'age': 'âge', 'education-num': 'niveau d’études', 'workclass': 'catégorie d’emploi',
    'marital-status': 'situation familiale', 'occupation': 'profession',
    'capital': 'revenus du capital', 'native_us': 'origine',
}


def _bundle():
    bundle = load_pipeline('hours')
    if not isinstance(bundle, dict) or any(k not in bundle for k in REQUIRED_KEYS):
        raise ModelNotReady(
            'Le fichier ml_models/hours/pipeline.joblib doit être le dictionnaire '
            'exporté par le notebook (clés : ' + ', '.join(REQUIRED_KEYS) + ').')
    return bundle


def normalize_profile(profile: dict) -> dict:
    """Valide les entrées du formulaire et les convertit en variables du notebook."""
    required = {'age', 'workclass', 'occupation', 'marital_status', 'capital_gain', 'capital_loss'}
    missing = required - set(profile)
    if missing:
        raise ValueError('Champs manquants : ' + ', '.join(sorted(missing)))
    age = int(profile['age'])
    if not 17 <= age <= 90:
        raise ValueError('Âge attendu entre 17 et 90 ans.')
    gain, loss = float(profile['capital_gain']), float(profile['capital_loss'])
    if gain < 0 or loss < 0:
        raise ValueError('Gains et pertes en capital ne peuvent pas être négatifs.')

    if 'education_num' in profile:
        edu_num = int(profile['education_num'])
    else:
        edu = str(profile.get('education', ''))
        edu_num = int(edu) if edu.isdigit() else EDUCATION_TO_NUM.get(edu)
        if edu_num is None:
            raise ValueError('Niveau d’études inconnu : ' + edu)
    if not 1 <= edu_num <= 16:
        raise ValueError('Niveau d’études attendu entre 1 et 16.')

    native = str(profile.get('native_us', profile.get('native-country', '1')))
    return {
        'age': age,
        'education-num': edu_num,
        'workclass': str(profile['workclass']),
        'marital-status': str(profile['marital_status']),
        'occupation': str(profile['occupation']),
        'log_capital_gain': math.log1p(gain),
        'log_capital_loss': math.log1p(loss),
        'has_capital': int(gain != 0 or loss != 0),
        'native_us': 1 if native in ('1', 'United-States', 'true', 'True') else 0,
    }


def build_row(values: dict, bundle: dict):
    """Reproduit pd.get_dummies(drop_first=True) puis StandardScaler du notebook."""
    import pandas as pd
    columns = list(bundle['colonnes'])
    row = dict.fromkeys(columns, 0)
    for name, value in values.items():
        if name in CATEGORICAL:
            if value not in bundle['categories'][name]:
                raise ValueError(f'Catégorie inconnue pour {name} : {value}')
            dummy = f'{name}_{value}'
            if dummy in row:          # la 1re catégorie (drop_first) reste à 0
                row[dummy] = 1
        elif name in row:
            row[name] = values[name]
    x = pd.DataFrame([row], columns=columns)
    x = x.astype({c: 'float64' for c in bundle['continues']})
    x[bundle['continues']] = bundle['scaler'].transform(x[bundle['continues']])
    return x


def _french_labels():
    """Libellés français du formulaire (catalogue) ; repli sur les valeurs brutes."""
    try:
        from portal.catalog import BY_SLUG
        return {f.key: dict(f.choices) for f in BY_SLUG['hours'].fields if f.kind == 'select'}
    except Exception:
        return {}


def top_factors(bundle: dict, x, values: dict, count: int = 3) -> list:
    """Les variables qui pèsent le plus dans CETTE prédiction (contributions XGBoost).

    Sens : « ↑ » pousse vers le temps partiel, « ↓ » vers le temps plein.
    Cela décrit l'usage du modèle, pas une cause réelle.
    """
    try:
        import xgboost as xgb
        contrib = bundle['modele'].get_booster().predict(xgb.DMatrix(x), pred_contribs=True)[0][:-1]
        by_col = dict(zip(bundle['colonnes'], contrib))
    except Exception:
        return []
    labels = _french_labels()
    scored = []
    for group, prefixes in GROUPS.items():
        total = sum(v for c, v in by_col.items() if any(c == p or (p.endswith('_') and c.startswith(p)) for p in prefixes))
        scored.append((abs(total), total, group))
    parts = []
    for _, total, group in sorted(scored, reverse=True)[:count]:
        if abs(total) < 0.05:
            continue
        key = {'marital-status': 'marital_status', 'education-num': 'education'}.get(group, group)
        if group == 'age':
            shown = f"{values['age']} ans"
        elif group == 'education-num':
            shown = f"{values['education-num']} ans d’études"
        elif group in ('workclass', 'marital-status', 'occupation'):
            shown = labels.get(key, {}).get(values[group], values[group])
        elif group == 'capital':
            shown = 'présents' if values['has_capital'] else 'aucun'
        else:
            shown = 'États-Unis' if values['native_us'] else 'autre pays'
        parts.append(f"{FACTOR_NAMES[group]} ({shown}) {'↑' if total > 0 else '↓'}")
    return parts


def predict(profile: dict) -> dict:
    """Point d'entrée appelé par Django et l'API JSON."""
    bundle = _bundle()
    values = normalize_profile(profile)
    try:
        x = build_row(values, bundle)
        proba = float(bundle['modele'].predict_proba(x)[0, 1])   # classe 1 = temps partiel
    except ValueError:
        raise
    except Exception as exc:
        raise ModelNotReady('Échec de la prédiction : vérifier les versions scikit-learn / xgboost '
                            'du modèle (voir bundle["versions"]).') from exc
    threshold = float(bundle['seuil'])
    part_time = proba >= threshold
    tier = 'high' if proba >= HIGH_PROBA else ('medium' if part_time else 'low')
    label, observed = TIERS[tier]
    factors = top_factors(bundle, x, values)
    note = (f'Parmi les profils de ce niveau dans le jeu de test, {observed} % étaient réellement à temps partiel '
            '(17 % en moyenne). ')
    if factors:
        note += ('Facteurs principaux (↑ vers le temps partiel, ↓ vers le temps plein) : '
                 + ' ; '.join(factors) + '. ')
    note += 'Estimation indicative, à ne pas utiliser pour une décision individuelle.'
    return {
        'label': label,
        'value': round(proba * 100, 1),
        'unit': '% de probabilité de temps partiel',
        'priority': tier,
        'probability_part_time': round(proba, 4),
        'threshold': threshold,
        'part_time': part_time,
        'factors': factors,
        'note': note,
    }
