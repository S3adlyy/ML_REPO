"""Create a reproducible, local-only deployment bundle of approved model files."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_FILES = [f'{slug}/pipeline.joblib' for slug in ('income','occupation','has_capital','hours','education','workclass')] + ['occupation/pipeline_complet.joblib']


def package(output):
    manifest = {'format': 1, 'files': {}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relative in MODEL_FILES:
            source = ROOT / 'ml_models' / relative
            data = source.read_bytes()
            manifest['files'][relative] = {'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)}
            entry = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data, compresslevel=6)
    manifest['bundle_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    (ROOT / 'ml_models' / 'deployment-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Packaged {len(MODEL_FILES)} files; {output.stat().st_size / 1024 / 1024:.1f} MiB. Nothing uploaded.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    package(parser.parse_args().output)
