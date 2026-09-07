import importlib.util
from pathlib import Path
import sys
import unittest


REPO = Path(__file__).resolve().parents[1]


def load(path: Path, name: str):
    sys.path.insert(0, str(REPO / "scripts"))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class Build134ReleaseContract(unittest.TestCase):
    def test_identity_uses_requested_bundle_and_build(self):
        identity = load(REPO / "scripts/jerkgram_finalize_build133_identity.py", "identity134")
        self.assertEqual(identity.PUBLIC_BUNDLE, "com.jerkgram.ios")
        self.assertEqual(identity.BUILD, "134")
        self.assertEqual(identity.TELEGRAM_VERSION, "12.9.2")
        self.assertEqual(identity.JERKGRAM_DISPLAY_VERSION, "1.0.2 Beta 2")
        self.assertEqual(identity.JERKGRAM_TECHNICAL_VERSION, "1.0.2-beta.2")

    def test_canonical_chain_keeps_last_good_telemetry_without_v2_overlay(self):
        hook = load(REPO / "scripts/install_jerkgram_v12w_build133_probe_hook.py", "hook134")
        self.assertNotIn("apply_jerkgram_v12y_build133_telemetry2.py", hook.SOURCE_ORDERED)
        self.assertNotIn("verify_jerkgram_v12y_build133_telemetry2.py", hook.SOURCE_ORDERED)

    def test_workflow_publishes_build134_artifact(self):
        workflow = (REPO / ".github/workflows/build.yml").read_text(encoding="utf-8")
        self.assertIn("name: Jerkgram 12.9.2 Build134", workflow)
        self.assertIn("name: Jerkgram-Build134", workflow)
        self.assertIn("artifacts/Jerkgram-Build134.ipa", workflow)
        self.assertIn("tests.test_jerkgram_build134_release_contract", workflow)


if __name__ == "__main__":
    unittest.main()
