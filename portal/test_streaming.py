import tempfile
from pathlib import Path
from django.test import SimpleTestCase
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from ml_modules.workclass.streaming import stream_forest


class StreamingForestTests(SimpleTestCase):
    def test_probabilities_and_classes_match_after_serialization(self):
        rng = np.random.default_rng(42)
        x = rng.normal(size=(90, 4))
        y = np.arange(90) % 3
        forest = RandomForestClassifier(n_estimators=11, random_state=42, n_jobs=2).fit(x, y)
        expected = forest.predict_proba(x)
        classes = forest.predict(x)
        with tempfile.TemporaryDirectory() as tmp:
            stream_forest(forest, tmp, tmp)
            path = Path(tmp) / 'forest.joblib'
            joblib.dump(forest, path)
            restored = joblib.load(path)
            np.testing.assert_allclose(restored.predict_proba(x), expected, rtol=1e-12, atol=1e-12)
            np.testing.assert_array_equal(restored.predict(x), classes)
            self.assertEqual(len(restored.estimators_), 11)
            self.assertEqual(restored.n_jobs, 1)
            self.assertLess(path.stat().st_size, 10000)
            (Path(tmp) / 'tree-0.joblib').unlink()
            with self.assertRaises(FileNotFoundError):
                restored.predict_proba(x)
