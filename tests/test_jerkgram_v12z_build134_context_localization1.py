from pathlib import Path
import importlib.util
import unittest


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts/apply_jerkgram_v12z_build134_context_localization1.py"
VERIFY = REPO / "scripts/verify_jerkgram_v12z_build134_context_localization1.py"
WORKFLOW = REPO / ".github/workflows/build.yml"
HOOK = REPO / "scripts/install_jerkgram_v12w_build133_probe_hook.py"


STRINGS_FIXTURE = r'''
public struct JerkgramStrings {
    public let languageCode: String
}
'''


MENU_FIXTURE = r'''
if ghostBaseShowEditHistory && !ghostBaseEditHistoryVersions.isEmpty {
    actions.append(.action(ContextMenuActionItem(text: "История", icon: { theme in
        return nil
    }, action: { _, f in
        let controller = makeController()
        controller.title = "История"
    })))
}

actions.append(.action(ContextMenuActionItem(
    text: "Переслать без автора",
    icon: { theme in nil },
    action: { _, f in }
)))
'''


class Build134ContextLocalizationTests(unittest.TestCase):
    def load_patch(self):
        spec = importlib.util.spec_from_file_location("build134_context_localization", PATCH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_strings_follow_telegram_language_with_english_fallback(self):
        module = self.load_patch()
        updated = module.patch_strings_text(STRINGS_FIXTURE)
        for token in (
            'var messageHistory: String',
            'self.languageCode == "ru" ? "История" : "History"',
            'var forwardWithoutAuthor: String',
            'self.languageCode == "ru" ? "Переслать без автора" : "Forward without author"',
        ):
            self.assertIn(token, updated)
        self.assertNotIn("Locale.current", updated)

    def test_context_row_history_row_and_history_title_are_localized(self):
        module = self.load_patch()
        updated = module.patch_menu_text(MENU_FIXTURE)
        self.assertIn(
            "text: chatPresentationInterfaceState.strings.jerkgram.messageHistory",
            updated,
        )
        self.assertIn(
            "controller.title = chatPresentationInterfaceState.strings.jerkgram.messageHistory",
            updated,
        )
        self.assertIn(
            "text: chatPresentationInterfaceState.strings.jerkgram.forwardWithoutAuthor",
            updated,
        )
        self.assertNotIn('text: "История"', updated)
        self.assertNotIn('controller.title = "История"', updated)
        self.assertNotIn('text: "Переслать без автора"', updated)

    def test_patch_is_idempotent(self):
        module = self.load_patch()
        strings = module.patch_strings_text(STRINGS_FIXTURE)
        menu = module.patch_menu_text(MENU_FIXTURE)
        self.assertEqual(module.patch_strings_text(strings), strings)
        self.assertEqual(module.patch_menu_text(menu), menu)

    def test_materialized_verifier_and_build_chain_include_owner(self):
        verifier = VERIFY.read_text(encoding="utf-8")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        hook = HOOK.read_text(encoding="utf-8")
        for token in (
            "verify_strings_owner",
            "verify_menu_owner",
            "Locale.current",
            "forwardWithoutAuthor",
            "messageHistory",
        ):
            self.assertIn(token, verifier)
        for owner in (workflow, hook):
            self.assertIn("apply_jerkgram_v12z_build134_context_localization1.py", owner)
            self.assertIn("verify_jerkgram_v12z_build134_context_localization1.py", owner)


if __name__ == "__main__":
    unittest.main()
