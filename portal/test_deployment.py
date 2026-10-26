import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
from django.test import SimpleTestCase
from scripts.fetch_models import install_bundle, validate_manifest


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
