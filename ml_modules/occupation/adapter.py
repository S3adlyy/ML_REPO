from ml_modules.common import predict_generic

# Noms des champs du formulaire (à gauche) -> colonnes du pipeline (à droite)
MAPPING = {
    "education_num": "education-num",
    "hours_per_week": "hours-per-week",
    "marital_status": "marital-status",
}

NOMS_GROUPES = {
    "0": "Plus âgés, peu diplômés",
    "1": "Jeunes célibataires",
    "2": "Hommes mariés, longues heures",
}


def predict(profile):
    resultat = predict_generic("occupation", profile, mapping=MAPPING, kind="clustering")
    resultat["label"] = NOMS_GROUPES.get(resultat["segment"], resultat["label"])
    resultat["note"] = "Profil type proche du vôtre, ce n'est pas une prédiction de métier."
    return resultat