import importlib.util
from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts/apply_jerkgram_v12za_build134_gift_localization1.py"
HOOK = REPO / "scripts/install_jerkgram_v12w_build133_probe_hook.py"
WORKFLOW = REPO / ".github/workflows/build.yml"


class SeasonalGiftLocalizationContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("seasonal_gifts", PATCH)
        cls.patch = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(cls.patch)

    def test_custom_seasonal_labels_follow_telegram_language(self):
        self.assertEqual(self.patch.seasonal_labels("ru"), ("Сезонные", "Сезонный"))
        self.assertEqual(self.patch.seasonal_labels("en"), ("Seasonal", "Seasonal"))
        self.assertEqual(self.patch.seasonal_labels("de"), ("Seasonal", "Seasonal"))

    def test_materialized_seasonal_owner_uses_selected_presentation_language(self):
        # This Build134 overlay runs after the legacy seasonal-gifts patch in
        # bazel_build_probe_official.sh. Unit tests run before materialization,
        # so model the two exact owners produced by that prerequisite instead
        # of reading the still-clean Official Telegram checkout.
        source = '''
                        TabSelectorComponent.Item(
                            id: AnyHashable(StarsFilter.seasonal.rawValue),
                            title: "Сезонные"
                        )
                        ribbon = GiftItemComponent.Ribbon(
                            text: "Сезонный",
                            color: .blue
                        )
'''
        updated = self.patch.patch_source(source)
        self.assertIn('strings.baseLanguageCode == "ru" ? "Сезонные" : "Seasonal"', updated)
        self.assertIn('environment.strings.baseLanguageCode == "ru" ? "Сезонный" : "Seasonal"', updated)
        self.assertNotIn('title: "Сезонные"', updated)
        self.assertNotIn('text: "Сезонный"', updated)

    def test_localization_gate_is_wired_before_the_build(self):
        hook = HOOK.read_text()
        workflow = WORKFLOW.read_text()
        for name in (
            "apply_jerkgram_v12za_build134_gift_localization1.py",
            "verify_jerkgram_v12za_build134_gift_localization1.py",
        ):
            self.assertIn(name, hook)
            self.assertIn(name, workflow)
        self.assertIn("tests.test_ghostbase_v10zb_seasonal_gifts_localization", workflow)


if __name__ == "__main__":
    unittest.main()
