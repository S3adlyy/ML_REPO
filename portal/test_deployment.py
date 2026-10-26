import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
from django.test import SimpleTestCase
from scripts.fetch_models import install_bundle, validate_manifest
import base64
import os
import subprocess
import sys


class RenderSettingsTests(SimpleTestCase):
    def load_settings(self, secret, on_render='true'):
        env = dict(os.environ, RENDER=on_render, DJANGO_DEBUG='0',
                   DJANGO_SECRET_KEY=secret,
                   DATABASE_URL='postgresql://test:test@localhost/test')
        return subprocess.run(
            [sys.executable, '-c', 'from config.settings import SECRET_KEY; print(SECRET_KEY)'],
            env=env, capture_output=True, text=True,
        )

    def test_render_generated_base64_secret_passes(self):
        secret = base64.b64encode(bytes(range(32))).decode()
        result = self.load_settings(secret)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), hashlib.sha256(secret.encode()).hexdigest())

    def test_short_or_malformed_secrets_still_fail(self):
        for secret in ('short', 'x' * 32, '!' * 44, 'dev-only-change-this-key-before-deployment'):
            with self.subTest(secret=secret):
                self.assertNotEqual(self.load_settings(secret).returncode, 0)

    def test_existing_long_secret_is_unchanged(self):
        secret = 'test-fixture-' + '0123456789abcdef' * 4
        result = self.load_settings(secret)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), secret)

    def test_base64_normalization_is_render_only(self):
        secret = base64.b64encode(bytes(range(32))).decode()
        self.assertNotEqual(self.load_settings(secret, 'false').returncode, 0)


class ModelBundleTests(SimpleTestCase):
    def make_bundle(self, root, entries):
        bundle = root / 'models.zip'
        with zipfile.ZipFile(bundle, 'w') as archive:
            for name, data in entries:
                archive.writestr(name, data)
        return bundle

    def manifest(self, bundle, files):
        return {'format':1,'bundle_sha256': hashlib.sha256(bundle.read_bytes()).hexdigest(), 'files': {name: {'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)} for name,data in files}}

    def test_exact_verified_bundle_is_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = [('income/pipeline.joblib', b'test fixture')]
            bundle = self.make_bundle(root, files)
            install_bundle(bundle, root / 'models', self.manifest(bundle, files))
            self.assertEqual((root/'models/income/pipeline.joblib').read_bytes(), b'test fixture')

    def test_tampered_bundle_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); files=[('income/pipeline.joblib',b'fixture')]
            bundle=self.make_bundle(root,files); manifest=self.manifest(bundle,files)
            bundle.write_bytes(bundle.read_bytes()+b'tampering')
            with self.assertRaises(ValueError): install_bundle(bundle,root/'models',manifest)
            self.assertFalse((root/'models').exists())

    def test_unexpected_archive_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); files=[('income/pipeline.joblib',b'fixture')]
            bundle=self.make_bundle(root,files+[('../escape.joblib',b'no')])
            with self.assertRaises(ValueError): install_bundle(bundle,root/'models',self.manifest(bundle,files))
            self.assertFalse((root/'models').exists())

    def test_unsafe_manifest_is_rejected(self):
        for name in ('../escape.joblib','/tmp/escape.joblib','income/../../escape.joblib'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_manifest({'format':1,'files':{name:{'size':5,'sha256':'unused'}}})

    def test_individual_checksum_mismatch_does_not_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); files=[('income/pipeline.joblib',b'fixture')]
            bundle=self.make_bundle(root,files); manifest=self.manifest(bundle,files)
            manifest['files']['income/pipeline.joblib']['sha256']='0'*64
            with self.assertRaises(ValueError): install_bundle(bundle,root/'models',manifest)
            self.assertFalse((root/'models').exists())
