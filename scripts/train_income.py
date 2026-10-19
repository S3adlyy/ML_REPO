"""Entraîne et exporte le modèle du module income (XGBoost réglé du notebook).

Commande depuis la racine du repo (environnement virtuel activé) :
    python scripts/train_income.py
    python scripts/train_income.py --data "C:/chemin/vers/adult-all.csv"

Produit (fichiers LOCAUX, jamais commités grâce au .gitignore) :
    ml_models/income/pipeline.joblib      pipeline complet : préparation + XGBoost
    ml_models/income/model_metadata.json  colonnes, seuil, labels, scores, versions
    ml_models/income/SHA256.txt           empreinte du .joblib (vérification d'intégrité)

Le pipeline reçoit les variables BRUTES du formulaire Django ; toute la préparation
du notebook (log1p du capital, education -> niveau ordonné, regroupement des
modalités rares) est faite DANS le pipeline, avec des transformateurs scikit-learn
standards uniquement (aucune fonction maison : le .joblib se recharge partout).
"""
import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, OrdinalEncoder
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'ml_models' / 'income'
RANDOM_STATE = 42

COLUMNS = ['age', 'workclass', 'fnlwgt', 'education', 'education-num', 'marital-status',
           'occupation', 'relationship', 'race', 'sex', 'capital-gain', 'capital-loss',
           'hours-per-week', 'native-country', 'income']

# Les 8 variables retenues dans le notebook (section 4.6), sous leur forme BRUTE
RAW_COLUMNS = ['age', 'education', 'workclass', 'occupation', 'relationship',
               'hours-per-week', 'capital-gain', 'capital-loss']

# Ordre officiel des niveaux d'études (= education-num 1 à 16)
EDUCATION_ORDER = ['Preschool', '1st-4th', '5th-6th', '7th-8th', '9th', '10th', '11th', '12th',
                   'HS-grad', 'Some-college', 'Assoc-voc', 'Assoc-acdm', 'Bachelors',
                   'Masters', 'Prof-school', 'Doctorate']

# Meilleurs réglages trouvés par RandomizedSearchCV dans le notebook (section 5.2)
XGB_PARAMS = dict(n_estimators=600, learning_rate=0.1, max_depth=5, min_child_weight=5,
                  reg_lambda=5, subsample=1.0, colsample_bytree=0.7)


def load_data(path):
    df = pd.read_csv(path, names=COLUMNS, skipinitialspace=True)
    df['income'] = df['income'].str.strip().str.rstrip('.')
    df = df.drop_duplicates().reset_index(drop=True)
    df = df.replace('?', 'Unknown')
    assert len(df) == 48790, f'Nettoyage différent de la référence du groupe ({len(df)} lignes au lieu de 48 790)'
    y = (df['income'] == '>50K').astype(int)
    return df[RAW_COLUMNS], y


def build_pipeline(scale_pos_weight):
    prep = ColumnTransformer([
        ('num', 'passthrough', ['age', 'hours-per-week']),
        ('log_capital', FunctionTransformer(np.log1p, feature_names_out='one-to-one'),
         ['capital-gain', 'capital-loss']),
        ('education_num', OrdinalEncoder(categories=[EDUCATION_ORDER],
                                         handle_unknown='use_encoded_value', unknown_value=-1),
         ['education']),
        # min_frequency=50 : les modalités très rares (Without-pay, Never-worked…) sont
        # regroupées automatiquement, comme le groupe « No-income » du notebook
        ('cat', OneHotEncoder(handle_unknown='infrequent_if_exist', min_frequency=50),
         ['workclass', 'occupation', 'relationship']),
    ], sparse_threshold=0)
    model = XGBClassifier(**XGB_PARAMS, scale_pos_weight=scale_pos_weight,
                          eval_metric='logloss', random_state=RANDOM_STATE)
    return Pipeline([('prep', prep), ('model', model)])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--data', default=str(ROOT / 'data' / 'adult-all.csv'),
                        help='chemin vers adult-all.csv (défaut : data/adult-all.csv)')
    args = parser.parse_args()
    data_path = Path(args.data)
    if not data_path.is_file():
        sys.exit(f'❌ Fichier introuvable : {data_path}\n   Placez adult-all.csv dans le dossier data/ ou utilisez --data.')

    X, y = load_data(data_path)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=RANDOM_STATE)
    ratio = float((y_train == 0).sum() / (y_train == 1).sum())
    print(f'✓ Données : {len(X)} lignes | train {len(X_train)} | test {len(X_test)}')

    # 1) Seuil de décision : choisi sur le TRAIN (prédictions out-of-fold), max F1
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    print('… choix du seuil par validation croisée (quelques secondes)')
    proba_oof = cross_val_predict(build_pipeline(ratio), X_train, y_train, cv=cv,
                                  method='predict_proba', n_jobs=-1)[:, 1]
    seuils = np.round(np.arange(0.05, 0.951, 0.01), 2)
    f1s = [f1_score(y_train, proba_oof >= t) for t in seuils]
    threshold = float(seuils[int(np.argmax(f1s))])
    print(f'✓ Seuil retenu (max F1 en CV) : {threshold:.2f}')

    # 2) Modèle final entraîné sur le train, évalué une seule fois sur le test
    pipeline = build_pipeline(ratio).fit(X_train, y_train)
    proba = pipeline.predict_proba(X_test)[:, 1]
    pred = (proba >= threshold).astype(int)
    metrics = {
        'roc_auc': round(roc_auc_score(y_test, proba), 4),
        'f1_positive': round(f1_score(y_test, pred), 4),
        'accuracy': round(accuracy_score(y_test, pred), 4),
        'balanced_accuracy': round(balanced_accuracy_score(y_test, pred), 4),
        'precision_positive': round(precision_score(y_test, pred), 4),
        'recall_positive': round(recall_score(y_test, pred), 4),
        'baseline_accuracy': round(float(1 - y_test.mean()), 4),
    }
    print('✓ Scores sur le test :', ', '.join(f'{k}={v}' for k, v in metrics.items()))

    # 3) Export
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model_file = OUT_DIR / 'pipeline.joblib'
    joblib.dump(pipeline, model_file)
    metadata = {
        'target': 'income',
        'label_mapping': {'0': '≤ 50 000 USD / an', '1': '> 50 000 USD / an'},
        'positive_class': 1,
        'raw_expected_columns': RAW_COLUMNS,
        'threshold': threshold,
        'threshold_rule': 'max F1 sur prédictions out-of-fold du train (5 plis)',
        'model': 'XGBoost réglé (XGBClassifier) dans un Pipeline scikit-learn',
        'hyperparameters': {**XGB_PARAMS, 'scale_pos_weight': round(ratio, 4)},
        'excluded_on_purpose': ['sex', 'race', 'marital-status', 'native-country', 'fnlwgt'],
        'test_metrics': metrics,
        'data_source': 'UCI Adult (adult-all.csv), 48 790 lignes après nettoyage, recensement US 1994',
        'model_is_decision_support_only': True,
        'training_seed': RANDOM_STATE,
        'trained_on': date.today().isoformat(),
        'versions': {'python': sys.version.split()[0], 'scikit-learn': sklearn.__version__,
                     'xgboost': xgboost.__version__, 'pandas': pd.__version__,
                     'numpy': np.__version__, 'joblib': joblib.__version__},
    }
    (OUT_DIR / 'model_metadata.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    digest = hashlib.sha256(model_file.read_bytes()).hexdigest()
    (OUT_DIR / 'SHA256.txt').write_text(f'{digest}  pipeline.joblib\n', encoding='utf-8')

    # 4) Vérification : on recharge le fichier comme Django le fera
    reloaded = joblib.load(model_file)
    exemple = pd.DataFrame([{'age': 45, 'education': 'Masters', 'workclass': 'Private',
                             'occupation': 'Exec-managerial', 'relationship': 'Husband',
                             'hours-per-week': 50, 'capital-gain': 0, 'capital-loss': 0}])
    p = float(reloaded.predict_proba(exemple)[0, 1])
    print(f'✓ Rechargement OK — exemple (45 ans, Master, cadre) : probabilité >50K = {p:.2f}')
    print('✓ Fichiers écrits dans ml_models/income/ : pipeline.joblib, model_metadata.json, SHA256.txt')


if __name__ == '__main__':
    main()
