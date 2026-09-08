import importlib.util
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
import zipfile


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


class Build135ReleaseContract(unittest.TestCase):
    def test_identity_uses_requested_bundle_and_build(self):
        identity = load(REPO / "scripts/jerkgram_finalize_build133_identity.py", "identity134")
        self.assertEqual(identity.PUBLIC_BUNDLE, "com.jerkgram.ios")
        self.assertEqual(identity.BUILD, "135")
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

    def test_workflow_publishes_build135_artifact(self):
        workflow = (REPO / ".github/workflows/build.yml").read_text(encoding="utf-8")
        self.assertIn("name: Jerkgram 12.9.2 Build135", workflow)
        self.assertIn("name: Jerkgram-Build135", workflow)
        self.assertIn("artifacts/Jerkgram-Build135.ipa", workflow)
        self.assertIn("tests.test_jerkgram_build134_release_contract", workflow)

    def test_finalizer_rebases_main_and_all_extension_bundle_identifiers(self):
        identity = load(REPO / "scripts/jerkgram_finalize_build133_identity.py", "identity134_rebase")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "Payload/Telegram.app"
            plugins = app / "PlugIns"
            plugins.mkdir(parents=True)
            (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "ph.telegra.Telegraph"}))
            for name, suffix in identity.EXTENSION_SUFFIXES.items():
                extension = plugins / name
                extension.mkdir()
                (extension / "Info.plist").write_bytes(plistlib.dumps({
                    "CFBundleIdentifier": "ph.telegra.Telegraph." + suffix,
                }))

            identity.rewrite_bundle_identifiers(root)

            with (app / "Info.plist").open("rb") as file:
                self.assertEqual(plistlib.load(file)["CFBundleIdentifier"], "com.jerkgram.ios")
            for name, suffix in identity.EXTENSION_SUFFIXES.items():
                with (plugins / name / "Info.plist").open("rb") as file:
                    self.assertEqual(
                        plistlib.load(file)["CFBundleIdentifier"],
                        "com.jerkgram.ios." + suffix,
                    )

    def test_final_verifier_accepts_only_complete_build135_namespace(self):
        verifier = load(REPO / "scripts/verify_jerkgram_v12w_build133_final_ipa.py", "verify_identity134")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "Payload/Telegram.app"
            plugins = app / "PlugIns"
            plugins.mkdir(parents=True)
            (app / "Info.plist").write_bytes(plistlib.dumps({
                "CFBundleIdentifier": "com.jerkgram.ios",
                "CFBundleShortVersionString": "12.9.2",
                "CFBundleVersion": "135",
                "CFBundleDisplayName": "Jerkgram",
                "CFBundleName": "Jerkgram",
            }))
            for name, suffix in verifier.EXTENSION_SUFFIXES.items():
                extension = plugins / name
                extension.mkdir()
                (extension / "Info.plist").write_bytes(plistlib.dumps({
                    "CFBundleIdentifier": "com.jerkgram.ios." + suffix,
                    "CFBundleVersion": "135",
                }))
            ipa = root / "Build135.ipa"
            with zipfile.ZipFile(ipa, "w") as archive:
                for path in (root / "Payload").rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(root))

            verifier.verify_build133_identity(ipa)

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
