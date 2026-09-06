#!/usr/bin/env python3
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
KEY = "jerkgram.Messages.HideBlockedReactions"


class Build132BlockedReactionPreferenceContractTests(unittest.TestCase):
    def test_runtime_readers_default_to_enabled_without_false_missing_key(self):
        paths = [
            SCRIPTS / "apply_build132_blocked_reactions_visibility.py",
            SCRIPTS / "apply_build132_blocked_reaction_list_filter.py",
            SCRIPTS / "apply_build132_blocked_reactions_rich_data.py",
        ]
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(f'bool(forKey: "{KEY}")', text, path.name)
            self.assertIn(f'object(forKey: "{KEY}") as? Bool', text, path.name)
            self.assertIn("?? true", text, path.name)

    def test_scoped_setting_is_mirrored_for_runtime_readers(self):
        text = (SCRIPTS / "apply_build132_blocked_reactions_visibility.py").read_text(encoding="utf-8")
        self.assertIn(
            f'UserDefaults.standard.set(state.hideBlockedReactions, forKey: "{KEY}")',
            text,
        )
        self.assertIn(
            'jerkgramPersistScopedSettingValues(accountPeerId: self.context.account.peerId.toInt64(), values: values)',
            text,
        )


if __name__ == "__main__":
    unittest.main()
