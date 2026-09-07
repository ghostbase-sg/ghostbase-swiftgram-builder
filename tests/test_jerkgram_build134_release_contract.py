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

    def test_canonical_chain_restores_telemetry_v2_1_after_release_identity(self):
        hook = load(REPO / "scripts/install_jerkgram_v12w_build133_probe_hook.py", "hook134")
        apply_name = "apply_jerkgram_v12y_build133_telemetry2.py"
        verify_name = "verify_jerkgram_v12y_build133_telemetry2.py"
        self.assertIn(apply_name, hook.SOURCE_ORDERED)
        self.assertIn(verify_name, hook.SOURCE_ORDERED)
        self.assertGreater(
            hook.SOURCE_ORDERED.index(apply_name),
            hook.SOURCE_ORDERED.index("apply_jerkgram_v12x_build133_release_ui1.py"),
        )

    def test_workflow_publishes_build134_artifact(self):
        workflow = (REPO / ".github/workflows/build.yml").read_text(encoding="utf-8")
        self.assertIn("name: Jerkgram 12.9.2 Build134", workflow)
        self.assertIn("name: Jerkgram-Build134", workflow)
        self.assertIn("artifacts/Jerkgram-Build134.ipa", workflow)
        self.assertIn("tests.test_jerkgram_build134_release_contract", workflow)

    def test_probe_hook_upgrades_an_existing_build133_block_to_v2_1(self):
        hook = load(REPO / "scripts/install_jerkgram_v12w_build133_probe_hook.py", "hook134_upgrade")
        old_order = [name for name in hook.SOURCE_ORDERED if "telemetry2" not in name]
        fixture = (
            hook.BUILD130_SOURCE_ANCHOR
            + "\n\n" + hook.SOURCE_MARKER + "\n"
            + "\n".join(hook.line(name) for name in old_order)
            + "\n" + hook.BAZEL_ANCHOR
            + "\n" + hook.BUILD130_FINAL_ANCHOR
            + "\n\n" + hook.FINAL_MARKER + "\n"
            + "\n".join(hook.line(name, "ghostbase-final/GhostBase.ipa") for name in hook.FINAL_ORDERED)
        )
        updated = hook.patch_probe(fixture)
        self.assertEqual(updated.count("apply_jerkgram_v12y_build133_telemetry2.py"), 1)
        self.assertEqual(updated.count("verify_jerkgram_v12y_build133_telemetry2.py"), 1)


if __name__ == "__main__":
    unittest.main()
