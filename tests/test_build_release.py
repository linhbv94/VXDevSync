import tempfile
import unittest
from pathlib import Path
from scripts.build_release import macos_chips, retire_unsupported_packages, VERSION


class MacosPackageArchitectureTests(unittest.TestCase):
    def test_arm64_does_not_get_an_intel_label(self):
        self.assertEqual(macos_chips('arm64\n'), ['silicon'])

    def test_intel_and_universal_payload_labels(self):
        self.assertEqual(macos_chips('x86_64'), ['intel'])
        self.assertEqual(macos_chips('x86_64 arm64'), ['silicon', 'intel'])

    def test_unknown_or_missing_architecture_fails_closed(self):
        for value in ('', 'arm64e', 'arm64 unsupported'):
            with self.assertRaises(RuntimeError):
                macos_chips(value)

    def test_old_mislabeled_assets_are_preserved_outside_upload_glob(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = root / 'dist'
            dist.mkdir()
            wrong = dist / f'vxdevsync_{VERSION}_macos_intel.dmg'
            wrong.write_bytes(b'old-arm64-payload')
            correct = dist / f'vxdevsync_{VERSION}_macos_silicon.dmg'
            correct.write_bytes(b'current-arm64-payload')
            retire_unsupported_packages(dist, ['silicon'])
            self.assertFalse(wrong.exists())
            moved = list((root / 'build').rglob(wrong.name))
            self.assertEqual(len(moved), 1)
            self.assertEqual(moved[0].read_bytes(), b'old-arm64-payload')
            self.assertEqual(correct.read_bytes(), b'current-arm64-payload')
