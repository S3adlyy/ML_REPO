"""Prepare a memory-bounded copy after the original bundle is verified."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
import pandas as pd
from ml_modules.workclass.adapter import model_path, EDUCATION_NUM
from ml_modules.workclass.streaming import stream_forest, source_digest


def main():
    source = model_path('workclass')
    artifact = joblib.load(source)
    pipeline = artifact['pipeline']
    # Diverse synthetic rows check preprocessing, class order and probabilities.
    rows = []
    for age in (18, 35, 65):
        for education in ('HS-grad', 'Bachelors', 'Masters'):
            for occupation in ('Sales', 'Adm-clerical'):
                rows.append({'age': age, 'education': education,
                    'education-num': EDUCATION_NUM[education], 'occupation': occupation,
                    'marital-status': 'Never-married', 'relationship': 'Not-in-family',
                    'race': 'White', 'sex': 'Male', 'hours-per-week': 40,
                    'capital-gain': 0, 'capital-loss': 0, 'income': '<=50K',
                    'native-country': 'United-States', 'workclass': 'Private', 'fnlwgt': 100000})
    frame = pd.DataFrame(rows)[artifact['input_columns']]
    expected = pipeline.predict_proba(frame)
    directory = source.parent / 'streamed'
    stream_forest(pipeline.steps[-1][1], directory, 'streamed')
    np.testing.assert_allclose(pipeline.predict_proba(frame), expected, rtol=1e-12, atol=1e-12)
    target = source.parent / 'pipeline-streamed.joblib'
    artifact['source_sha256'] = source_digest(source)
    joblib.dump(artifact, target)
    restored = joblib.load(target)
    np.testing.assert_allclose(restored['pipeline'].predict_proba(frame), expected, rtol=1e-12, atol=1e-12)
    print(f'Workclass: all {pipeline.steps[-1][1].n_estimators} trees preserved; {len(frame)} probability comparisons passed.')


if __name__ == '__main__':
    main()
