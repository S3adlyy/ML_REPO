"""Download and verify the exact approved artifact bundle before any unpickling."""
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_DOWNLOAD = 300 * 1024 * 1024


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def validate_manifest(manifest):
    if manifest.get('format') != 1 or not manifest.get('files'):
        raise ValueError('Invalid model manifest')
    for name, info in manifest['files'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or len(path.parts) != 2 or path.suffix != '.joblib':
            raise ValueError('Unsafe model path in manifest')
        if not isinstance(info.get('size'), int) or not 0 < info['size'] < 300 * 1024 * 1024:
            raise ValueError('Invalid model size')


def verify_local(model_root, manifest):
    return all((model_root / name).is_file() and (model_root / name).stat().st_size == info['size'] and digest(model_root / name) == info['sha256'] for name, info in manifest['files'].items())


def install_bundle(bundle, model_root, manifest):
    validate_manifest(manifest)
    if digest(bundle) != manifest['bundle_sha256']:
        raise ValueError('Model bundle checksum mismatch')
    # Validate every entry before writing to the destination; never extract arbitrary paths.
    with zipfile.ZipFile(bundle) as archive, tempfile.TemporaryDirectory() as staging:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(manifest['files']):
            raise ValueError('Unexpected model bundle contents')
        for name, info in manifest['files'].items():
            entry = archive.getinfo(name)
            if entry.file_size != info['size']:
                raise ValueError('Model size mismatch')
            staged = Path(staging) / name
            staged.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, staged.open('wb') as target:
                shutil.copyfileobj(source, target)
            if digest(staged) != info['sha256']:
                raise ValueError('Individual model checksum mismatch')
        for name in names:
            target = model_root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(staging) / name, target)


def main():
    manifest = json.loads((ROOT / 'ml_models' / 'deployment-manifest.json').read_text())
    validate_manifest(manifest)
    model_root = ROOT / 'ml_models'
    if verify_local(model_root, manifest):
        print('All approved models already present and verified.')
        return
    url = os.getenv('MODEL_BUNDLE_URL', '')
    if not url.startswith('https://'):
        raise SystemExit('Set MODEL_BUNDLE_URL to the HTTPS location of the approved bundle before deployment.')
    try:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / 'models.zip'
            with urllib.request.urlopen(url, timeout=120) as response, bundle.open('wb') as target:
                if not response.geturl().startswith('https://'):
                    raise ValueError('Insecure download redirect')
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_DOWNLOAD:
                        raise ValueError('Model bundle too large')
                    target.write(chunk)
            install_bundle(bundle, model_root, manifest)
    except Exception:
        # Signed URLs can contain secrets, so do not print request exceptions or URLs.
        raise SystemExit('Model download or verification failed. Check the bundle URL and manifest.') from None
    print('All seven artifacts installed and checksum-verified.')


if __name__ == '__main__':
    main()
