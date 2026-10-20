from ml_modules.common import predict_generic
from ml_modules.occupation.recommandations import NOMS_GROUPES, recommander

# Noms des champs du formulaire (à gauche) -> colonnes du pipeline (à droite)
MAPPING = {
    "education_num": "education-num",
    "hours_per_week": "hours-per-week",
    "marital_status": "marital-status",
}


def predict(profile):
    resultat = predict_generic("occupation", profile, mapping=MAPPING, kind="clustering")
    segment = resultat["segment"]
    resultat["label"] = NOMS_GROUPES.get(segment, resultat["label"])
    resultat["note"] = "Profil type proche du vôtre, ce n'est pas une prédiction de métier."
    resultat["reco"] = recommander(segment, profile)
    return resultat
