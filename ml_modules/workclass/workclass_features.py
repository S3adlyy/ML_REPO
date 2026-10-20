"""Prétraitement partagé entre l'entraînement et l'inférence (prédiction de workclass)."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

# Colonnes brutes attendues en entrée du modèle
RAW_INPUT_COLUMNS = [
    "age", "education", "education-num", "marital-status", "occupation",
    "relationship", "race", "sex", "capital-gain", "capital-loss",
    "hours-per-week", "native-country", "income",
]
NUMERIC_RAW = ["age", "education-num", "capital-gain", "capital-loss", "hours-per-week"]
TEXT_RAW = ["education", "marital-status", "occupation", "relationship", "race", "sex",
            "native-country", "income"]


def _clean_text(s, rstrip=None):
    """Supprime les espaces, transforme '?' en valeur manquante (et retire un suffixe éventuel)."""
    s = s.astype("string").str.strip()
    if rstrip:
        s = s.str.rstrip(rstrip)
    s = s.replace("?", pd.NA)
    return s.astype(object).where(s.notna(), np.nan)


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Nettoyage + variables dérivées du groupe, à partir des colonnes brutes."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X[RAW_INPUT_COLUMNS].copy()
        for col in TEXT_RAW:
            X[col] = _clean_text(X[col], rstrip="." if col == "income" else None)
        for col in ["occupation", "native-country"]:
            X[col] = X[col].fillna("Unknown")
        for col in NUMERIC_RAW:
            X[col] = pd.to_numeric(X[col], errors="coerce")
        X[["capital-gain", "capital-loss"]] = X[["capital-gain", "capital-loss"]].fillna(0)

        X["log_capital_gain"] = np.log1p(X["capital-gain"])
        X["log_capital_loss"] = np.log1p(X["capital-loss"])
        X["has_capital"] = ((X["capital-gain"] != 0) | (X["capital-loss"] != 0)).astype(int)
        X["native_us"] = (X["native-country"] == "United-States").astype(int)
        return X
