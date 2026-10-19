# Modèles de l'équipe

Chaque membre place son pipeline **entraîné et validé** dans :

```text
ml_models/<slug>/pipeline.joblib
```

Le modèle `education` est fourni dans cette archive pour une démo locale ; `model_metadata.json` décrit les colonnes d'entrée, les labels et le seuil de décision `0.52`. Les cinq autres emplacements sont vides.

**GitHub :** les fichiers `.joblib` sont volontairement exclus de Git par `.gitignore` (un modèle `pickle`/`joblib` peut exécuter du code à l'ouverture). Distribuez vos artefacts approuvés par un canal séparé ou une release privée et vérifiez les versions des dépendances. Ne publiez pas de données personnelles.
