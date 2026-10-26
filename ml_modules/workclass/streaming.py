"""Read trusted forest trees one at a time for the free Render instance."""
from collections.abc import Sequence
from pathlib import Path
import hashlib


def source_digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


class TreeFiles(Sequence):
    def __init__(self, directory, count):
        self.directory = str(directory)
        self.count = count

    def __len__(self):
        return self.count

    def __getitem__(self, index):
        if not isinstance(index, int):
            raise TypeError('Tree indices must be integers')
        if index < 0:
            index += self.count
        if not 0 <= index < self.count:
            raise IndexError(index)
        import joblib
        root = Path(__file__).resolve().parents[2] / 'ml_models' / 'workclass'
        return joblib.load(root / self.directory / f'tree-{index}.joblib')


def stream_forest(forest, output, runtime_directory):
    """Preserve all fitted trees and sklearn inference, changing only storage."""
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    if not isinstance(forest, RandomForestClassifier):
        raise ValueError('Expected the approved RandomForestClassifier')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    count = len(forest.estimators_)
    for index, tree in enumerate(forest.estimators_):
        joblib.dump(tree, output / f'tree-{index}.joblib')
    forest.estimators_ = TreeFiles(runtime_directory, count)
    # Parallel inference would retain multiple trees and increase memory use.
    forest.n_jobs = 1
