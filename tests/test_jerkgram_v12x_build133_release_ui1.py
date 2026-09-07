from pathlib import Path
import importlib.util
import unittest


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts/apply_jerkgram_v12x_build133_release_ui1.py"
VERIFY = REPO / "scripts/verify_jerkgram_v12x_build133_release_ui1.py"
FINAL_VERIFY = REPO / "scripts/verify_jerkgram_v12w_build133_final_ipa.py"


SETTINGS_FIXTURE = r'''
// MARK: Jerkgram v1.2L BUILD123_SETTINGS_SYSTEM1
private func JerkgramSettingsStatusItem(
    presentationData: ItemListPresentationData,
    text: String,
    sectionId: ItemListSectionId
) -> ListViewItem {
    return ItemListDisclosureItem(
        presentationData: presentationData,
        systemStyle: .glass,
        title: text,
        label: "",
        labelStyle: .text,
        sectionId: sectionId,
        style: .blocks,
        disclosureStyle: .none,
        action: nil
    )
}

private func ghostBaseSettingsEntries(state: GhostBaseSettingsState, page: GhostBaseSettingsPage, strings: JerkgramStrings) -> [GhostBaseSettingsEntry] {
    if page == .messages {
        return [
            .header(0, strings.messages),
            .info(1, "messages footer")
        ]
    }
    if page == .appearance {
        return [
            .header(0, strings.appearance),
            .info(1, "appearance footer")
        ]
    }
    if page == .about {
        return [
            .header(0, strings.about),
            .info(1, strings.build124AboutSummary)
        ]
    }
    return []
}
'''

STRINGS_FIXTURE = r'''
public struct JerkgramStrings {
    public let languageCode: String
}

public extension JerkgramStrings {
    var build124AboutSummary: String {
        return "Jerkgram · Official Telegram 12.9.2 · Build 124 Canary"
    }
}
'''


class Build133ReleaseUIContractTests(unittest.TestCase):
    def load_patch(self):
        spec = importlib.util.spec_from_file_location("build133_release_ui", PATCH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_status_info_returns_to_native_plain_text(self):
        module = self.load_patch()
        updated = module.patch_settings_text(SETTINGS_FIXTURE)
        status = module.block_text(updated, "private func JerkgramSettingsStatusItem(")
        self.assertIn("ItemListTextItem(", status)
        self.assertIn("text: .plain(text)", status)
        self.assertNotIn("ItemListDisclosureItem(", status)
        self.assertNotIn("systemStyle: .glass", status)
        self.assertNotIn("style: .blocks", status)
        self.assertIn(".info(1, \"messages footer\")", updated)
        self.assertIn(".info(1, \"appearance footer\")", updated)

    def test_about_uses_single_release_identity(self):
        module = self.load_patch()
        updated = module.patch_strings_text(STRINGS_FIXTURE)
        for token in (
            'displayVersion = "1.0.2 Beta 1"',
            'technicalVersion = "1.0.2-beta.1"',
            'build = "133"',
            'telegramBase = "12.9.2"',
            '"Jerkgram Version \\(displayVersion)\\nBuild \\(build)\\nTelegram Base \\(telegramBase)"',
        ):
            self.assertIn(token, updated)
        about = module.block_text(updated, "var build124AboutSummary: String {")
        self.assertIn("JerkgramReleaseIdentity.aboutText", about)
        self.assertNotIn("Build 124 Canary", about)

    def test_final_ipa_contract_keeps_public_telegram_identity(self):
        source = FINAL_VERIFY.read_text(encoding="utf-8")
        self.assertIn('EXPECTED_BUNDLE = "ph.telegra.Telegraph"', source)
        self.assertIn('EXPECTED_TELEGRAM_VERSION = "12.9.2"', source)
        self.assertIn('EXPECTED_BUILD = "133"', source)
        self.assertIn("CFBundleShortVersionString", source)

    def test_materialized_verifier_rejects_glass_status_owner(self):
        source = VERIFY.read_text(encoding="utf-8")
        for token in (
            "verify_settings_owner",
            "verify_release_strings",
            "ItemListTextItem(",
            "systemStyle: .glass",
            "JerkgramReleaseIdentity",
            "1.0.2 Beta 1",
            "1.0.2-beta.1",
            "Telegram Base",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
