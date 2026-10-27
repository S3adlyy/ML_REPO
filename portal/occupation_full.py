"""Module occupation : deux onglets.

1. « Vue d'ensemble » : tableau de bord statique (sans formulaire) sur la population,
   construit à partir des résultats du notebook (9 variables, mêmes profils que le formulaire).
2. « Trouver mon groupe » : formulaire à 9 variables (pipeline ml_models/occupation/pipeline.joblib).

Cette page n'ajoute pas de module au catalogue (accueil et /health/ inchangés).
"""
import logging

from django.shortcuts import render

from ml_modules.common import ModelNotReady, model_installed

from .catalog import BY_SLUG
from ml_modules.occupation.recommandations import GROUPES, PISTES

from .forms import create_profile_form

log = logging.getLogger(__name__)

def _f(x):
    """Nombre au format français, en texte (Django localiserait les floats et casserait les largeurs CSS)."""
    return str(x).replace('.', ',')


# Profils types de la population (mêmes trois profils que le formulaire ; 48 790 personnes, 9 variables).
_PISTES = {k: [(t, d) for t, d, _ in v] for k, v in PISTES.items()}
PROFILES = [
    dict(name=GROUPES['0']['nom'], color='orange', size=23.3, age=53.5, hours=36.2, edu=8.3, women=43, high=9, capital=11,
         marital='Married-civ-spouse (46 %)', rel='Husband (38 %)', work='Private (64 %)', occ='Craft-repair (14 %)',
         blurb='Plus âgés, souvent mariés, avec moins d’années d’études : beaucoup d’expérience, mais peu de hauts revenus.',
         pistes=_PISTES['0']),
    dict(name=GROUPES['1']['nom'], color='teal', size=39.2, age=27.1, hours=36.0, edu=9.8, women=50, high=2, capital=6,
         marital='Never-married (75 %)', rel='Not-in-family (37 %)', work='Private (78 %)', occ='Adm-clerical (16 %)',
         blurb='Jeunes, majoritairement célibataires, en début de parcours : très peu de hauts revenus pour l’instant.',
         pistes=_PISTES['1']),
    dict(name=GROUPES['2']['nom'], color='violet', size=37.6, age=41.5, hours=47.7, edu=11.4, women=9, high=56, capital=21,
         marital='Married-civ-spouse (86 %)', rel='Husband (81 %)', work='Private (64 %)', occ='Prof-specialty (21 %)',
         blurb='Carrière installée, mariés, longues semaines de travail : plus d’un sur deux gagne plus de 50K.',
         pistes=_PISTES['2']),
]
for _p in PROFILES:
    _p.update(size_txt=_f(_p['size']) + ' %', age_txt=_f(_p['age']), hours_txt=_f(_p['hours']), edu_txt=_f(_p['edu']), size_w=str(_p['size']))

# Comparaison des profils sur quelques indicateurs : (titre, clé, unité, échelle maximale)
_METRICS = [('Âge moyen', 'age', 'ans', 60), ('Heures travaillées par semaine', 'hours', 'h', 50), ('Années d’études', 'edu', 'ans', 16),
            ('Revenu supérieur à 50K', 'high', '%', 100), ('Part de femmes', 'women', '%', 100)]
METRICS = [dict(title=t, unit=u, bars=[dict(color=p['color'], name=p['name'], txt=_f(p[k]) + (' %' if u == '%' else ' ' + u),
                                            w=str(round(p[k] / mx * 100))) for p in PROFILES]) for t, k, u, mx in _METRICS]

# Indicateurs de toute la population (moyennes pondérées des profils, arrondies)
KPIS = [('48 790', 'personnes étudiées'), ('≈ 38,6 ans', 'âge moyen'), ('≈ 40,5 h', 'travaillées par semaine'),
        ('≈ 24 %', 'gagnent plus de 50K'), ('≈ 33 %', 'de femmes')]

TAKEAWAYS = [
    ('Trois profils, deux grands blocs', 'Les Nouveaux Départs (39,2 %) et Les Bâtisseurs (37,6 %) regroupent les trois quarts de la population ; Les Expérimentés en représentent 23,3 %.'),
    ('Le revenu suit la carrière installée', '56 % des Bâtisseurs gagnent plus de 50K, contre 9 % des Expérimentés et 2 % des Nouveaux Départs.'),
    ('Les Bâtisseurs travaillent le plus', '47,7 heures par semaine en moyenne, contre environ 36 heures dans les deux autres profils.'),
    ('Les études font la différence', '11,4 ans d’études chez Les Bâtisseurs, contre 9,8 chez Les Nouveaux Départs et 8,3 chez Les Expérimentés.'),
    ('Les femmes sont peu présentes chez les Bâtisseurs', '9 % de femmes dans ce profil, contre 50 % chez Les Nouveaux Départs et 43 % chez Les Expérimentés.'),
]


def occupation_dashboard(request):
    return render(request, 'portal/occupation_dashboard.html', {
        'module': BY_SLUG['occupation'], 'profiles': PROFILES, 'metrics': METRICS, 'takeaways': TAKEAWAYS, 'kpis': KPIS,
        'active': 'occupation', 'occ_variant': 'vue',
    })


def occupation_profil(request):
    """Onglet « Trouver mon groupe » : formulaire à 9 variables."""
    from .views import execute
    module = BY_SLUG['occupation']
    form = create_profile_form(module, data=request.POST if request.method == 'POST' else None)
    result, warning = None, None
    if request.method == 'POST' and form.is_valid():
        try:
            result = execute(module, form.cleaned_data)
        except ModelNotReady as exc:
            warning = str(exc)
        except Exception:
            log.exception('Erreur de prédiction occupation')
            warning = 'Prédiction indisponible. Vérifiez le pipeline, les variables et les versions de dépendances.'
    return render(request, 'portal/module.html', {
        'module': module, 'form': form, 'result': result, 'warning': warning,
        'installed': model_installed('occupation'), 'active': 'occupation', 'occ_variant': 'profil',
    })
