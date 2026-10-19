"""Entraînement et sauvegarde du pipeline de classification has_capital.

Auteur : Bilal El Eter (Membre 03)
Projet : Adult UCI Machine Learning
Cible : has_capital (1 si capital-gain > 0 ou capital-loss > 0, 0 sinon)

Ce script reproduit à 100% le notebook validé et exporte :
- ml_models/has_capital/pipeline.joblib
- ml_models/has_capital/model_metadata.json
- ml_models/has_capital/exemple_profil.json
"""
import json
import os
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_CANDIDATES = [
    ROOT.parent.parent / "adult-all.csv",
    ROOT.parent / "adult-all.csv",
    ROOT / "adult-all.csv",
    Path("adult-all.csv"),
    Path("../adult-all.csv"),
    Path("../../adult-all.csv"),
]


DATA_PATH = None
for p in DATA_CANDIDATES:
    if p.is_file():
        DATA_PATH = p
        break

if DATA_PATH is None:
    raise FileNotFoundError("adult-all.csv introuvable dans le workspace.")

print(f"Chargement des données depuis : {DATA_PATH}")

columns = [
    "age", "workclass", "fnlwgt", "education", "education-num",
    "marital-status", "occupation", "relationship", "race", "sex",
    "capital-gain", "capital-loss", "hours-per-week", "native-country", "income"
]

df = pd.read_csv(DATA_PATH, names=columns, skipinitialspace=True)
df.drop_duplicates(inplace=True)
df.reset_index(drop=True, inplace=True)
df = df.replace("?", np.nan)
for col in df.columns[df.isnull().any()]:
    val = df[col].median() if pd.api.types.is_numeric_dtype(df[col]) else "Unknown"
    df[col] = df[col].fillna(val)

df = df.drop(columns=["fnlwgt"])
df["log_capital_gain"] = np.log1p(df["capital-gain"])
df["log_capital_loss"] = np.log1p(df["capital-loss"])
df["has_capital"] = ((df["capital-gain"] != 0) | (df["capital-loss"] != 0)).astype(int)
df["native_us"] = (df["native-country"] == "United-States").astype(int)

# Préparation individuelle Bilal : exclusion stricte des fuites et de la cible
leakage_cols = ["capital-gain", "capital-loss", "log_capital_gain", "log_capital_loss"]
df_bilal = df.drop(columns=leakage_cols + ["education", "native-country"])

TARGET = "has_capital"
X_all = df_bilal.drop(columns=[TARGET])
y = df_bilal[TARGET]

RANDOM_STATE = 42
X_train_full, X_test_full, y_train, y_test = train_test_split(
    X_all, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
)

# 9 variables explicatives retenues (race et sex retirées conformément à l'étude d'ablation)
FINAL_COLS = [
    "age", "workclass", "education-num", "marital-status",
    "occupation", "relationship", "hours-per-week", "income", "native_us"
]
SCALE_COLS = ["age", "education-num", "hours-per-week"]
BIN_COLS = ["native_us"]
CAT_COLS = ["workclass", "marital-status", "occupation", "relationship", "income"]

preprocessor = ColumnTransformer([
    ("num", StandardScaler(), SCALE_COLS),
    ("bin", "passthrough", BIN_COLS),
    ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_COLS),
], sparse_threshold=0)

model = HistGradientBoostingClassifier(
    class_weight="balanced",
    learning_rate=0.05,
    max_iter=300,
    early_stopping=True,
    random_state=RANDOM_STATE,
)

pipeline = Pipeline([
    ("prep", preprocessor),
    ("model", model),
])

print("Entraînement du pipeline...")
pipeline.fit(X_train_full[FINAL_COLS], y_train)

# Optimisation du seuil par CV 5-folds sur le train
print("Validation croisée pour calibrer le seuil optimal...")
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
oof = cross_val_predict(pipeline, X_train_full[FINAL_COLS], y_train, cv=cv, method="predict_proba", n_jobs=-1)[:, 1]

RAPPEL_MIN, MARGE = 0.45, 0.02
res_cv = []
for t in np.arange(0.01, 0.99, 0.005):
    pred = (oof >= t).astype(int)
    res_cv.append({
        "th": t,
        "acc": accuracy_score(y_train, pred),
        "rec": recall_score(y_train, pred),
        "prec": precision_score(y_train, pred, zero_division=0),
    })

res_cv_df = pd.DataFrame(res_cv)
ok = res_cv_df[res_cv_df["rec"] >= RAPPEL_MIN + MARGE]
best_th = round(float(ok.loc[ok["acc"].idxmax(), "th"]), 3)
print(f"Seuil optimal calibré : {best_th}")

# Évaluation sur le jeu de test
Xte = X_test_full[FINAL_COLS]
s_test = pipeline.predict_proba(Xte)[:, 1]
p_opt = (s_test >= best_th).astype(int)

pr_auc = float(average_precision_score(y_test, s_test))
roc_auc = float(roc_auc_score(y_test, s_test))
acc_opt = float(accuracy_score(y_test, p_opt))
rec_opt = float(recall_score(y_test, p_opt))
prec_opt = float(precision_score(y_test, p_opt, zero_division=0))

k = int(len(y_test) * 0.10)
top10_idx = np.argsort(-s_test)[:k]
top10_pos = float(y_test.values[top10_idx].mean())
lift_top10 = round(top10_pos / float(y_test.mean()), 2)

print(f"Test PR-AUC   : {pr_auc:.4f}")
print(f"Test ROC-AUC  : {roc_auc:.4f}")
print(f"Test Accuracy : {acc_opt:.4f}")
print(f"Test Rappel   : {rec_opt:.4f}")
print(f"Test Précision: {prec_opt:.4f}")
print(f"Lift top 10%  : x{lift_top10}")

# Sauvegarde des artefacts
OUT_DIR = ROOT / "ml_models" / "has_capital"
OUT_DIR.mkdir(parents=True, exist_ok=True)

model_path = OUT_DIR / "pipeline.joblib"
joblib.dump(pipeline, model_path)
print(f"Pipeline sauvegardé dans : {model_path}")

metadata = {
    "target": "has_capital",
    "target_description": "Propension à détenir des actifs ou déclarer des gains/pertes de capital (1 = oui, 0 = non)",
    "label_mapping": {
        "0": "Aucun capital significatif déclaré (has_capital = 0)",
        "1": "Détention de capital probable (has_capital = 1)",
    },
    "features": FINAL_COLS,
    "raw_expected_columns": FINAL_COLS,
    "threshold": best_th,
    "model": "HistGradientBoostingClassifier",
    "class_weight": "balanced",
    "imbalance_technique": "Class Weight (retenue après comparaison de 5 techniques)",
    "leakage_prevention": [
        "capital-gain exclu",
        "capital-loss exclu",
        "log_capital_gain exclu",
        "log_capital_loss exclu",
    ],
    "sensitive_features_removed": ["race", "sex"],
    "metrics_test": {
        "pr_auc": round(pr_auc, 3),
        "roc_auc": round(roc_auc, 3),
        "accuracy": round(acc_opt, 3),
        "recall": round(rec_opt, 3),
        "precision": round(prec_opt, 3),
        "lift_top_10_percent": lift_top10,
    },
    "model_is_decision_support_only": True,
    "author": "Bilal El Eter (Membre 03)",
    "training_seed": RANDOM_STATE,
}

meta_path = OUT_DIR / "model_metadata.json"
meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Métadonnées sauvegardées dans : {meta_path}")

exemple = {
    "age": 35,
    "education": "Bachelors",
    "workclass": "Private",
    "occupation": "Exec-managerial",
    "hours_per_week": 45,
    "marital_status": "Married-civ-spouse",
    "relationship": "Husband",
    "income": ">50K",
    "native_us": "1",
}
exemple_path = OUT_DIR / "exemple_profil.json"
exemple_path.write_text(json.dumps(exemple, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Exemple sauvegardé dans : {exemple_path}")
print("[OK] Entraînement et génération des artefacts has_capital terminés avec succès.")

