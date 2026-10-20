"""Module occupation : deux onglets.

1. « Vue d'ensemble » : tableau de bord statique (sans formulaire) sur la population,
   construit à partir des résultats du notebook (13 variables).
2. « Trouver mon groupe » : formulaire à 9 variables (pipeline ml_models/occupation/pipeline.joblib).

Cette page n'ajoute pas de module au catalogue (accueil et /health/ inchangés).
"""
import logging

from django.shortcuts import render

from ml_modules.common import ModelNotReady, model_installed

from .catalog import BY_SLUG
from .forms import create_profile_form

log = logging.getLogger(__name__)

def _f(x):
    """Nombre au format français, en texte (Django localiserait les floats et casserait les largeurs CSS)."""
    return str(x).replace('.', ',')


# Profils types de la population (résultats du notebook, 48 790 personnes).
PROFILES = [
    dict(name='Jeunes, majorité jamais mariés', color='teal', size=45.5, age=28.3, hours=36.3, edu=9.4, women=43, high=5, gain=1, loss=0,
         marital='Never-married (61 %)', rel='Not-in-family (32 %)', work='Private (78 %)', occ='Adm-clerical (15 %)',
         blurb='Personnes jeunes, souvent célibataires, avec peu de hauts revenus.'),
    dict(name='Plus âgés, majorité mariés', color='violet', size=49.8, age=47.8, hours=44.0, edu=10.6, women=25, high=39, gain=16, loss=0,
         marital='Married-civ-spouse (67 %)', rel='Husband (61 %)', work='Private (62 %)', occ='Exec-managerial (18 %)',
         blurb='Personnes plus âgées, mariées, qui travaillent plus et gagnent davantage.'),
    dict(name='Pertes de capital', color='orange', size=4.7, age=41.8, hours=43.3, edu=11.0, women=24, high=50, gain=0, loss=100,
         marital='Married-civ-spouse (62 %)', rel='Husband (55 %)', work='Private (65 %)', occ='Exec-managerial (20 %)',
         blurb='Petit groupe : toutes les personnes déclarent une perte de capital, et un sur deux gagne plus de 50K.'),
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
    ('Deux grandes moitiés', 'La population se partage presque à égalité entre des personnes jeunes (45,5 %, 28 ans en moyenne) et des personnes plus âgées (49,8 %, 48 ans).'),
    ('Le revenu monte avec l’âge et la vie de famille', '39 % des plus âgés, majoritairement mariés, gagnent plus de 50K, contre 5 % des plus jeunes.'),
    ('Les plus âgés travaillent plus', '44 heures par semaine en moyenne, contre 36 heures pour les plus jeunes.'),
    ('Les femmes sont plus présentes chez les jeunes', '43 % de femmes dans le groupe des jeunes, contre 25 % chez les plus âgés.'),
    ('Le capital concerne une minorité', 'Seuls 4,7 % déclarent une perte de capital et environ 8 % un gain : ces personnes ont les revenus les plus élevés.'),
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
