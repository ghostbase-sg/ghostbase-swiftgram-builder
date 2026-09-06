import importlib.util
from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts" / "apply_jerkgram_v12u_build133_blocked_activity1.py"
VERIFY = REPO / "scripts" / "verify_jerkgram_v12u_build133_blocked_activity1.py"


class Build133BlockedActivityContracts(unittest.TestCase):
    @staticmethod
    def load(path: Path, name: str):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def setUp(self):
        self.patch = self.load(PATCH, "build133_blocked_activity_patch")

    def test_only_blocked_mention_has_no_target(self):
        targets = [(1, "A", True)]
        self.assertIsNone(self.patch.visible_navigation_target(targets, {"A"}, enabled=True))

    def test_blocked_then_allowed_targets_allowed(self):
        targets = [(1, "A", True), (2, "B", True)]
        self.assertEqual(self.patch.visible_navigation_target(targets, {"A"}, enabled=True), 2)

    def test_removed_message_is_not_navigable(self):
        targets = [(1, "B", False), (2, "C", True)]
        self.assertEqual(self.patch.visible_navigation_target(targets, set(), enabled=True), 2)

    def test_feature_off_preserves_stock_first_existing_target(self):
        targets = [(1, "A", True), (2, "B", True)]
        self.assertEqual(self.patch.visible_navigation_target(targets, {"A"}, enabled=False), 1)

    def test_unknown_actor_is_preserved(self):
        targets = [(1, None, True)]
        self.assertEqual(self.patch.visible_navigation_target(targets, {"A"}, enabled=True), 1)

    def test_chat_list_activity_hidden_when_complete_set_is_blocked(self):
        self.assertFalse(
            self.patch.visible_activity(
                stock=True,
                summary_count=1,
                loaded=[("A", True)],
                blocked={"A"},
                enabled=True,
            )
        )

    def test_chat_list_activity_preserved_when_allowed_exists(self):
        self.assertTrue(
            self.patch.visible_activity(
                stock=True,
                summary_count=2,
                loaded=[("A", True), ("B", True)],
                blocked={"A"},
                enabled=True,
            )
        )

    def test_chat_list_activity_preserves_stock_if_loaded_evidence_incomplete(self):
        self.assertTrue(
            self.patch.visible_activity(
                stock=True,
                summary_count=2,
                loaded=[("A", True)],
                blocked={"A"},
                enabled=True,
            )
        )

    def test_verifier_contract_exists(self):
        verify = self.load(VERIFY, "build133_blocked_activity_verify")
        self.assertTrue(callable(verify.verify_chat_list_owner))
        self.assertTrue(callable(verify.verify_navigation_owner))


if __name__ == "__main__":
    unittest.main()
