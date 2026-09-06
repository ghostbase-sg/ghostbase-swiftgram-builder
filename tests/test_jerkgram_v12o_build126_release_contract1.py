from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[1]


def current_workflow_build() -> int:
    workflow = (REPO / ".github/workflows/build.yml").read_text(encoding="utf-8")
    match = re.search(r"name:\s+Jerkgram 12\.9\.2 Build(\d+)", workflow)
    if match is None:
        raise AssertionError("current Jerkgram build identity missing from workflow")
    return int(match.group(1))


class Build126ReleaseContractTests(unittest.TestCase):
    def test_build128_finalization_preserves_keychain_and_file_picker_payload(self):
        finalizer = REPO / "scripts" / "jerkgram_finalize_build128_identity.py"
        verifier = REPO / "scripts" / "verify_jerkgram_v12s_build128_final_ipa.py"
        publisher = REPO / "scripts" / "jerkgram_publish_build128_artifact.py"
        for path in (finalizer, verifier, publisher):
            self.assertTrue(path.is_file(), f"missing Build128 release owner: {path.name}")

        verifier_text = verifier.read_text(encoding="utf-8")
        self.assertIn("sideloadKeychainFix.dylib", verifier_text)
        self.assertIn("file_picker.FILE_PICKER_NAME", verifier_text)

        # Build130 remains a historical wrapper in the chain. Do not require it
        # to be the currently published release forever.
        self.assertIn(
            'base.base.BUILD = "130"',
            (REPO / "scripts" / "jerkgram_finalize_build130_identity.py").read_text(encoding="utf-8"),
        )
        self.assertIn(
            'base.base.EXPECTED_BUILD = "130"',
            (REPO / "scripts" / "verify_jerkgram_v12s_build130_final_ipa.py").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "Jerkgram-Build130.ipa",
            (REPO / "scripts" / "jerkgram_publish_build130_artifact.py").read_text(encoding="utf-8"),
        )

    def test_workflow_publishes_only_current_successor_artifact(self):
        workflow = (REPO / ".github/workflows/build.yml").read_text(encoding="utf-8")
        build = current_workflow_build()
        self.assertGreaterEqual(build, 128)
        self.assertIn("jerkgram_finalize_build128_identity.py", workflow)
        self.assertIn("verify_jerkgram_v12s_build128_final_ipa.py", workflow)
        self.assertIn(f"jerkgram_publish_build{build}_artifact.py", workflow)
        self.assertIn(f"Jerkgram-Build{build}", workflow)


if __name__ == "__main__":
    unittest.main()
