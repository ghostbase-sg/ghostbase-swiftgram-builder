from pathlib import Path
import importlib.util
import unittest

REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts/apply_jerkgram_build140_identity.py"
FINALIZER = REPO / "scripts/jerkgram_finalize_build133_identity.py"
FINAL_VERIFY = REPO / "scripts/verify_jerkgram_v12w_build133_final_ipa.py"
PUBLISHER = REPO / "scripts/jerkgram_publish_build138_artifact.py"

FIXTURE = '''
// MARK: Jerkgram v1.2X BUILD133_RELEASE_IDENTITY1
public enum JerkgramReleaseIdentity {
    public static let displayVersion = "1.0.2"
    public static let technicalVersion = "1.0.2"
    public static let build = "139"
    public static let telegramBase = "12.9.2"

    public static var aboutText: String {
        return "Jerkgram Version \\(displayVersion)\\nBuild \\(build)\\nTelegram Base \\(telegramBase)"
    }
}
'''


class Build140IdentityTests(unittest.TestCase):
    def load_patch(self):
        spec = importlib.util.spec_from_file_location("build140_identity", PATCH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_advances_release_identity_to_build140_and_is_idempotent(self):
        module = self.load_patch()
        updated = module.patch_text(FIXTURE)
        self.assertIn('public static let build = "140"', updated)
        self.assertNotIn('public static let build = "139"', updated)
        self.assertIn('public static let displayVersion = "1.0.2"', updated)
        self.assertIn('public static let technicalVersion = "1.0.2"', updated)
        self.assertIn('public static let telegramBase = "12.9.2"', updated)
        self.assertEqual(updated, module.patch_text(updated))

    def test_physical_ipa_identity_is_build140_everywhere(self):
        finalizer = FINALIZER.read_text(encoding="utf-8")
        verifier = FINAL_VERIFY.read_text(encoding="utf-8")
        publisher = PUBLISHER.read_text(encoding="utf-8")

        self.assertIn('BUILD = "140"', finalizer)
        self.assertIn("base.base.base.BUILD = BUILD", finalizer)
        self.assertIn('CFBundleVersion=140', finalizer)
        self.assertNotIn('BUILD = "138"', finalizer)

        self.assertIn('EXPECTED_BUILD = "140"', verifier)
        self.assertIn('CFBundleVersion is not 140', verifier)
        self.assertNotIn('EXPECTED_BUILD = "138"', verifier)

        self.assertIn('base.EXPECTED_BUILD = "140"', publisher)
        self.assertIn('Build=140', publisher)
        self.assertNotIn('base.EXPECTED_BUILD = "138"', publisher)

    def test_rejects_unexpected_previous_build(self):
        module = self.load_patch()
        with self.assertRaises(RuntimeError):
            module.patch_text(FIXTURE.replace('build = "139"', 'build = "137"'))


if __name__ == "__main__":
    unittest.main()
