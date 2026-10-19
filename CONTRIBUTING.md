# Contribution · un repo, six membres

## Branches

- `main` : version stable et démontrable
- `develop` : intégration (optionnelle)
- `feature/income`, `feature/occupation`, `feature/age`, `feature/hours`, `feature/education`, `feature/workclass` : travail indépendant

## Règles

1. Créer sa branche depuis `main` ou `develop` (choisir une stratégie d'équipe et s'y tenir).
2. Modifier en priorité `ml_modules/<slug>/adapter.py`, `portal/catalog.py` (uniquement l'entrée de son module) et `requirements-ml.example.txt` si besoin.
3. NE PAS inclure CSV, modèles `.joblib`, `.env`, bases SQLite, données personnelles dans Git.
4. Adapter la liste des features du formulaire au pipeline final : encodage entraîné dans le pipeline et pas dans la vue.
5. Valider avec `python manage.py check && python manage.py test`.
6. Ouvrir une Pull Request vers `develop` ou `main`, demander un avis d'un autre membre.
7. Résoudre les conflits sur `portal/catalog.py` ensemble ; chacun édite seulement son entrée.

## Contrat commun des modules

```python
# ml_modules/<slug>/adapter.py
# profile: dict nettoyé par le formulaire
# retourner un dict JSON-serializable avec au moins la clé 'label'
def predict(profile: dict) -> dict:
    return {'label': 'Résultat', 'note': 'Estimation, pas une décision.'}
```

L'appel côté Django se fait via `portal.views.execute()`. Ne modifiez pas la vue globale pour brancher votre modèle.

## Tests locaux / API

Une requête POST vers `/api/modules/<slug>/predict/` retourne `503` tant que le modèle est absent, et `400` si le profil est invalide. Les clients navigateur doivent envoyer le jeton CSRF.
