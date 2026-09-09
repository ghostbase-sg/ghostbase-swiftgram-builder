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

private func build133SyntheticRenderer(
    presentationData: ItemListPresentationData,
    sectionId: ItemListSectionId
) -> [ListViewItem] {
    return [
        ItemListSwitchItem(
            presentationData: presentationData,
            systemStyle: .glass,
            title: "Messages toggle",
            value: true,
            sectionId: sectionId,
            style: .blocks,
            updated: { _ in }
        ),
        ItemListDisclosureItem(
            presentationData: presentationData,
            systemStyle: .glass,
            title: "Appearance",
            label: "",
            labelStyle: .text,
            sectionId: sectionId,
            style: .blocks,
            disclosureStyle: .arrow,
            action: nil
        )
    ]
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
            .header(1, strings.version),
            .aboutValue(1, 1, strings.jerkgramVersion, Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "—"),
            .aboutValue(1, 2, strings.build, Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "—"),
            .aboutValue(1, 3, strings.telegramBase, "12.9.2"),
            .header(2, strings.privacy),
            .info(3, "analytics footer")
        ]
    }
    return []
}
'''

STRINGS_FIXTURE = r'''
// MARK: Jerkgram v1.2M BUILD124_SETTINGS_REDESIGN_STRINGS1
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

    def test_status_is_plain_and_interactive_rows_keep_large_glass_rounding(self):
        module = self.load_patch()
        updated = module.patch_settings_text(SETTINGS_FIXTURE)
        status = module.block_text(updated, "private func JerkgramSettingsStatusItem(")
        self.assertIn("ItemListTextItem(", status)
        self.assertIn("text: .plain(text)", status)
        self.assertNotIn("ItemListDisclosureItem(", status)
        self.assertNotIn("systemStyle: .glass", status)
        self.assertNotIn("style: .blocks", status)
        renderer = module.block_text(updated, "private func build133SyntheticRenderer(")
        switch_owner, disclosure_owner = renderer.split("ItemListDisclosureItem(", 1)
        self.assertIn("systemStyle: .glass", switch_owner)
        self.assertIn("systemStyle: .glass", disclosure_owner)
        self.assertIn(".info(1, \"messages footer\")", updated)
        self.assertIn(".info(1, \"appearance footer\")", updated)

    def test_real_about_rows_use_single_release_identity_not_plist_version(self):
        module = self.load_patch()
        updated = module.patch_settings_text(SETTINGS_FIXTURE)
        about = module.block_text(updated, "if page == .about {")
        self.assertIn("strings.jerkgramVersion, JerkgramReleaseIdentity.displayVersion", about)
        self.assertIn("strings.build, JerkgramReleaseIdentity.build", about)
        self.assertIn("strings.telegramBase, JerkgramReleaseIdentity.telegramBase", about)
        self.assertNotIn("CFBundleShortVersionString", about)
        self.assertNotIn("CFBundleVersion", about)

    def test_release_strings_hold_beta2_display_and_technical_identity(self):
        module = self.load_patch()
        updated = module.patch_strings_text(STRINGS_FIXTURE)
        for token in (
            'displayVersion = "1.0.2 Beta 2"',
            'technicalVersion = "1.0.2-beta.2"',
            'build = "137"',
            'telegramBase = "12.9.2"',
            '"Jerkgram Version \\(displayVersion)\\nBuild \\(build)\\nTelegram Base \\(telegramBase)"',
        ):
            self.assertIn(token, updated)
        summary = module.block_text(updated, "var build124AboutSummary: String {")
        self.assertIn("JerkgramReleaseIdentity.aboutText", summary)
        self.assertNotIn("Build 124 Canary", summary)

    def test_existing_release_identity_advances_to_current_build(self):
        module = self.load_patch()
        previous = module.patch_strings_text(STRINGS_FIXTURE).replace(
            'build = "137"', 'build = "136"'
        )
        updated = module.patch_strings_text(previous)
        self.assertIn('build = "137"', updated)
        self.assertNotIn('build = "136"', updated)
        self.assertEqual(updated, module.patch_strings_text(updated))

    def test_final_ipa_contract_keeps_last_good_public_telegram_identity(self):
        source = FINAL_VERIFY.read_text(encoding="utf-8")
        self.assertIn('EXPECTED_BUNDLE = "com.jerkgram.ios"', source)
        self.assertIn('EXPECTED_TELEGRAM_VERSION = "12.9.2"', source)
        self.assertIn('EXPECTED_BUILD = "137"', source)
        self.assertIn('EXPECTED_DISPLAY = "Jerkgram"', source)
        self.assertIn("CFBundleShortVersionString", source)

    def test_materialized_verifier_rejects_any_settings_glass_and_wrong_about_owner(self):
        source = VERIFY.read_text(encoding="utf-8")
        for token in (
            "verify_settings_owner",
            "verify_release_strings",
            "ItemListTextItem(",
            "systemStyle: .glass",
            "JerkgramReleaseIdentity",
            "CFBundleShortVersionString",
            "1.0.2 Beta 2",
            "1.0.2-beta.2",
            "Telegram Base",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
