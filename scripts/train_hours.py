"""Régénère ml_models/hours/pipeline.joblib (modèle temps partiel, Bessem) avec les
versions du dépôt. Reprend exactement le notebook Projet_ML_Adult_Bessem_final.

Usage depuis la racine :  python scripts/train_hours.py chemin/vers/adult-all.csv
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost as xgb
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.preprocessing import StandardScaler

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'ml_models' / 'hours' / 'pipeline.joblib'
CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'adult-all.csv'
# Meilleurs hyperparamètres trouvés par RandomizedSearchCV dans le notebook
PARAMS = dict(subsample=0.6, reg_lambda=10, reg_alpha=0, n_estimators=400, max_depth=5,
              learning_rate=0.05, gamma=1, colsample_bytree=1.0)

columns = ['age', 'workclass', 'fnlwgt', 'education', 'education-num', 'marital-status', 'occupation',
           'relationship', 'race', 'sex', 'capital-gain', 'capital-loss', 'hours-per-week',
           'native-country', 'income']
df = pd.read_csv(CSV, names=columns, skipinitialspace=True)
df = df.drop_duplicates().reset_index(drop=True).replace('?', np.nan)
for col in df.columns[df.isnull().any()]:
    df[col] = df[col].fillna(df[col].median() if pd.api.types.is_numeric_dtype(df[col]) else 'Unknown')
df = df.drop(columns=['fnlwgt'])
df['log_capital_gain'] = np.log1p(df['capital-gain'])
df['log_capital_loss'] = np.log1p(df['capital-loss'])
df['has_capital'] = ((df['capital-gain'] != 0) | (df['capital-loss'] != 0)).astype(int)
df['native_us'] = (df['native-country'] == 'United-States').astype(int)

df_b = df.copy()
df_b['income_high'] = (df_b['income'].str.strip().str.rstrip('.') == '>50K').astype(int)
df_b = df_b.drop(columns=['education', 'income', 'capital-gain', 'capital-loss', 'native-country'])

y = df_b['hours-per-week']
tranches = pd.cut(y, [0, 30, 39, 40, 50, 100])
X_enc_all = pd.get_dummies(df_b.drop(columns='hours-per-week'),
                           columns=df_b.drop(columns='hours-per-week').select_dtypes(exclude='number').columns.tolist(),
                           drop_first=True, dtype=int)
train_idx, test_idx = train_test_split(df_b.index, test_size=0.2, random_state=42, stratify=tranches)

y_c = (y <= 34).astype(int)
X_c = df_b.drop(columns=['hours-per-week', 'sex', 'race', 'relationship', 'income_high'])
cat_c = X_c.select_dtypes(exclude='number').columns.tolist()
X_enc_c = pd.get_dummies(X_c, columns=cat_c, drop_first=True, dtype=int)
continues = ['age', 'education-num', 'log_capital_gain', 'log_capital_loss']
X_tr, X_te = X_enc_c.loc[train_idx].copy(), X_enc_c.loc[test_idx].copy()
y_tr, y_te = y_c.loc[train_idx], y_c.loc[test_idx]
scaler = StandardScaler()
X_tr[continues] = scaler.fit_transform(X_tr[continues])
X_te[continues] = scaler.transform(X_te[continues])
cols = X_tr.columns.tolist()

oof = cross_val_predict(xgb.XGBClassifier(random_state=42, n_jobs=-1, **PARAMS), X_tr, y_tr,
                        cv=StratifiedKFold(5, shuffle=True, random_state=42), method='predict_proba')[:, 1]
seuils = np.arange(0.05, 0.80, 0.01)
seuil = float(seuils[np.argmax([f1_score(y_tr, oof >= s) for s in seuils])])
model = xgb.XGBClassifier(random_state=42, n_jobs=-1, **PARAMS).fit(X_tr, y_tr)
proba = model.predict_proba(X_te)[:, 1]
pred = (proba >= seuil).astype(int)
metrics = {'AUC': roc_auc_score(y_te, proba), 'F1': f1_score(y_te, pred), 'precision': precision_score(y_te, pred),
           'rappel': recall_score(y_te, pred), 'Accuracy': accuracy_score(y_te, pred)}

OUT.parent.mkdir(parents=True, exist_ok=True)
joblib.dump({
    'modele': model, 'scaler': scaler, 'colonnes': cols, 'continues': continues, 'seuil': seuil,
    'categories': {c: sorted(df_b[c].unique().tolist()) for c in cat_c},
    'metriques': {k: float(v) for k, v in metrics.items()}, 'taux_base': float(y_c.mean()),
    'versions': {'scikit-learn': sklearn.__version__, 'xgboost': xgb.__version__},
}, OUT)
print('Colonnes :', len(cols), '| seuil :', round(seuil, 2))
print({k: round(float(v), 3) for k, v in metrics.items()})
print('✓ Modèle écrit dans', OUT)
