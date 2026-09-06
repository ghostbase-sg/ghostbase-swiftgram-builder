import importlib.util
from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts" / "apply_jerkgram_v12t_build133_blocked_reactions1.py"
VERIFY = REPO / "scripts" / "verify_jerkgram_v12t_build133_blocked_reactions1.py"


class Build133BlockedReactionContracts(unittest.TestCase):
    def load(self, path: Path, name: str):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def setUp(self):
        self.patch = self.load(PATCH, "build133_blocked_reactions_patch")

    def filter(self, reactions, recent, blocked, *, account="ME", enabled=True):
        return self.patch.filter_reaction_model(
            reactions=reactions,
            recent_peers=recent,
            blocked_peer_ids=set(blocked),
            account_peer_id=account,
            enabled=enabled,
        )

    def test_sole_blocked_reactor_removes_pill(self):
        reactions, recent = self.filter(
            [("👍", 1, False)],
            [("👍", "A", False)],
            {"A"},
        )
        self.assertEqual(reactions, [])
        self.assertEqual(recent, [])

    def test_mixed_same_reaction_decrements_count(self):
        reactions, recent = self.filter(
            [("👍", 2, False)],
            [("👍", "A", False), ("👍", "B", False)],
            {"A"},
        )
        self.assertEqual(reactions, [("👍", 1, False)])
        self.assertEqual(recent, [("👍", "B", False)])

    def test_mixed_reaction_kinds_remove_only_blocked_contribution(self):
        reactions, recent = self.filter(
            [("👍", 1, False), ("❤️", 1, False)],
            [("👍", "A", False), ("❤️", "B", False)],
            {"A"},
        )
        self.assertEqual(reactions, [("❤️", 1, False)])
        self.assertEqual(recent, [("❤️", "B", False)])

    def test_feature_off_is_stock(self):
        original_reactions = [("👍", 2, False)]
        original_recent = [("👍", "A", False), ("👍", "B", False)]
        reactions, recent = self.filter(
            original_reactions,
            original_recent,
            {"A"},
            enabled=False,
        )
        self.assertEqual(reactions, original_reactions)
        self.assertEqual(recent, original_recent)

    def test_empty_blocked_set_is_stock(self):
        original_reactions = [("👍", 1, False)]
        original_recent = [("👍", "A", False)]
        reactions, recent = self.filter(original_reactions, original_recent, set())
        self.assertEqual(reactions, original_reactions)
        self.assertEqual(recent, original_recent)

    def test_own_reaction_is_never_removed(self):
        reactions, recent = self.filter(
            [("👍", 1, True)],
            [("👍", "ME", True)],
            {"ME"},
        )
        self.assertEqual(reactions, [("👍", 1, True)])
        self.assertEqual(recent, [("👍", "ME", True)])

    def test_unknown_actor_is_preserved(self):
        reactions, recent = self.filter(
            [("👍", 1, False)],
            [("👍", None, False)],
            {"A"},
        )
        self.assertEqual(reactions, [("👍", 1, False)])
        self.assertEqual(recent, [("👍", None, False)])

    def test_verifier_contract_exists(self):
        verify = self.load(VERIFY, "build133_blocked_reactions_verify")
        self.assertTrue(callable(verify.verify_policy_source))
        self.assertTrue(callable(verify.verify_reaction_owner))
        self.assertTrue(callable(verify.verify_list_owner))


if __name__ == "__main__":
    unittest.main()
