import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Build125CanaryPublicationTests(unittest.TestCase):
    def test_workflow_can_advance_past_build125_with_a_successor_artifact(self):
        workflow = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
        match = re.search(r"name:\s+Jerkgram 12\.9\.2 Build(\d+)", workflow)
        self.assertIsNotNone(match)
        successor_build = int(match.group(1))
        self.assertGreater(successor_build, 125)
        self.assertIn(f"Jerkgram-Build{successor_build}", workflow)
        self.assertIn(f"jerkgram_publish_build{successor_build}_artifact.py", workflow)

    def test_final_identity_and_verifier_require_build125(self):
        identity = (ROOT / "scripts/jerkgram_finalize_build125_identity.py").read_text(encoding="utf-8")
        verifier = (ROOT / "scripts/verify_jerkgram_v12n_build125_final_ipa.py").read_text(encoding="utf-8")
        self.assertIn('base.BUILD = "125"', identity)
        self.assertIn('base.EXPECTED_BUILD = "125"', verifier)
        self.assertIn("api_verify.verify_ipa_credentials", verifier)


if __name__ == "__main__":
    unittest.main()
