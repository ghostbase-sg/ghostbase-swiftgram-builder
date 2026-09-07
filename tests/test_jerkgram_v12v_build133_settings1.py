import importlib.util
from pathlib import Path
import re
import sys
import unittest


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts" / "apply_jerkgram_v12v_build133_settings1.py"
VERIFY = REPO / "scripts" / "verify_jerkgram_v12v_build133_settings1.py"


class Build133SettingsContracts(unittest.TestCase):
    @staticmethod
    def load(path: Path, name: str):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def setUp(self):
        self.patch = self.load(PATCH, "build133_settings_patch")

    def test_exact_english_strings(self):
        self.assertEqual(
            self.patch.localized_settings_strings("en"),
            ("BLOCKED USERS", "Hide Blocked Messages", "Hide Blocked Reactions"),
        )

    def test_exact_russian_strings(self):
        self.assertEqual(
            self.patch.localized_settings_strings("ru"),
            ("ЗАБЛОКИРОВАННЫЕ", "Скрывать сообщения заблокированных", "Скрывать реакции заблокированных"),
        )

    def test_non_russian_falls_back_to_english(self):
        self.assertEqual(
            self.patch.localized_settings_strings("de"),
            self.patch.localized_settings_strings("en"),
        )

    def test_messages_rows_use_native_toggle_entry_with_existing_trailing_comma(self):
        # Reproduces Build133 #710: the canonical Messages array already ends
        # its last element with a comma. The overlay must not emit a second one.
        fixture = '''
private enum GhostBaseKey {
    static let saveDeleted = "Jerkgram.Messages.SaveDeleted"
}
private struct GhostBaseSettingsState: Equatable {
    var saveDeleted: Bool
    static func load() -> GhostBaseSettingsState {
        return GhostBaseSettingsState(
            saveDeleted: true
        )
    }
    func save() {
        UserDefaults.standard.set(self.saveDeleted, forKey: GhostBaseKey.saveDeleted)
    }
}
private func ghostBaseSettingsEntries(state: GhostBaseSettingsState, context: AccountContext, page: GhostBaseSettingsPage, strings: JerkgramStrings) -> [GhostBaseSettingsEntry] {
    if page == .messages {
        return [
            .header(0, strings.deletedMessages),
            .toggle(0, 1, GhostBaseKey.saveDeleted, strings.saveDeletedMessages, state.saveDeleted),
        ]
    }
    return []
}
private func f() {
    switch key {
    case GhostBaseKey.saveDeleted:
        updated.saveDeleted = value
    default:
        break
    }
}
'''
        result = self.patch.patch_settings_text(fixture)
        self.assertIn("strings.blockedUsers", result)
        self.assertIn("strings.hideBlockedMessages", result)
        self.assertIn("strings.hideBlockedReactions", result)
        self.assertIn(".toggle(1, 1, GhostBaseKey.hideBlockedMessages", result)
        self.assertIn(".toggle(1, 2, GhostBaseKey.hideBlockedReactions", result)
        self.assertIsNone(
            re.search(r",\s*,\s*\.header\(1,\s*strings\.blockedUsers\)", result),
            result,
        )
        self.assertNotIn("UISwitch(", result)
        self.assertNotIn("switch.frame", result)

    def test_storage_keys_are_stable(self):
        self.assertEqual(self.patch.HIDE_BLOCKED_MESSAGES_KEY, "jerkgram.Messages.HideBlockedMessages")
        self.assertEqual(self.patch.HIDE_BLOCKED_REACTIONS_KEY, "jerkgram.Messages.HideBlockedReactions")

    def test_blocked_visibility_settings_are_committed_before_runtime_notification(self):
        sys.path.insert(0, str(REPO / "scripts"))
        try:
            patch2 = self.load(REPO / "scripts/apply_jerkgram_v12v_build133_settings2.py", "build133_settings2_sync")
        finally:
            sys.path.pop(0)
        fixture = '''    let jerkgramSynchronousRuntimeSettingKeys: Set<String> = [
        GhostBaseKey.scheduledSend,
        GhostBaseKey.protectedEnabled,
        GhostBaseKey.oneTimeSave,
    ]
    let defaults = UserDefaults.standard
    for key in jerkgramSynchronousRuntimeSettingKeys {
        guard let value = changes[key] else { continue }
        value.write(to: defaults, key: key)
    }

    let deferredChanges = changes.filter {
'''
        patch_commit = getattr(patch2, "patch_blocked_runtime_commit", None)
        if not callable(patch_commit):
            self.fail("blocked runtime settings commit owner is not patchable")
        updated = patch_commit(fixture)
        self.assertIn("GhostBaseKey.hideBlockedMessages", updated)
        self.assertIn("GhostBaseKey.hideBlockedReactions", updated)
        self.assertLess(
            updated.index("value.write(to: defaults, key: key)"),
            updated.index("JerkgramBlockedReactionPolicy.notifySettingsChanged()"),
        )

    def test_verifier_contract_exists(self):
        verify = self.load(VERIFY, "build133_settings_verify")
        self.assertTrue(callable(verify.verify_strings))
        self.assertTrue(callable(verify.verify_settings))


if __name__ == "__main__":
    unittest.main()
