#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
PATCHER = REPO / "scripts" / "apply_build132_blocked_reactions_visibility.py"


def load_patcher():
    spec = importlib.util.spec_from_file_location("build132_blocked_reactions_visibility", PATCHER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Build132 blocked reaction patcher")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Build132BlockedReactionSettingsTests(unittest.TestCase):
    def test_toggle_is_localized_and_mirrored_to_runtime_preference(self):
        module = load_patcher()
        source = '''    static let hideBlockedMessages = "jerkgram.Messages.HideBlockedMessages"\n\n    var hideBlockedMessages: Bool\n\n            hideBlockedMessages: jerkgramScopedBool(accountPeerId: accountPeerId, key: GhostBaseKey.hideBlockedMessages, defaultValue: true),\n\n        GhostBaseKey.hideBlockedMessages: .bool(state.hideBlockedMessages),\n\n            .toggle(\n                1,\n                90,\n                GhostBaseKey.hideBlockedMessages,\n                "Скрывать сообщения заблокированных",\n                state.hideBlockedMessages\n            ),\n\n            case GhostBaseKey.hideBlockedMessages:\n                updated.hideBlockedMessages = value\n'''
        result = module.patch_settings(source)

        self.assertIn("Hide blocked users' messages", result)
        self.assertIn("Hide blocked users' reactions", result)
        self.assertIn('strings.languageCode == "ru"', result)
        self.assertIn(
            "UserDefaults.standard.set(value, forKey: GhostBaseKey.hideBlockedReactions)",
            result,
        )
        self.assertIn(
            "hideBlockedReactions: jerkgramScopedBool(accountPeerId: accountPeerId, key: GhostBaseKey.hideBlockedReactions, defaultValue: false)",
            result,
        )


if __name__ == "__main__":
    unittest.main()
