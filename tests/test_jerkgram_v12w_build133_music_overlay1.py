import importlib.util
from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts" / "apply_jerkgram_v12w_build133_music_overlay1.py"
VERIFY = REPO / "scripts" / "verify_jerkgram_v12w_build133_music_overlay1.py"


class Build133MusicOverlayContracts(unittest.TestCase):
    @staticmethod
    def load(path: Path, name: str):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def setUp(self):
        self.patch = self.load(PATCH, "build133_music_patch_test")

    @staticmethod
    def official_fixture() -> str:
        return '''final class OverlayAudioPlayerControllerNode: ViewControllerTracingNode, ASGestureRecognizerDelegate {
    let controls = OverlayAudioPlayerControlsNode(
    let history = ChatHistoryListNodeImpl(
        systemStyle: .glass,
        self.albumArtBackground = UIVisualEffectView()
        self.dimNode.backgroundColor = UIColor(white: 0.0, alpha: 0.5)
        self.historyBackgroundContentNode.backgroundColor = self.presentationData.theme.list.itemModalBlocksBackgroundColor
        self.historyFrameLeftOverlayNode.backgroundColor = self.presentationData.theme.list.modalBlocksBackgroundColor
        self.historyFrameRightOverlayNode.backgroundColor = self.presentationData.theme.list.modalBlocksBackgroundColor
        self.historyFrameTopOverlayNode.backgroundColor = self.presentationData.theme.list.modalBlocksBackgroundColor
        self.historyBackgroundContentNode.backgroundColor = self.hasAnyHistoryMessages == true ? self.presentationData.theme.list.itemModalBlocksBackgroundColor : self.presentationData.theme.list.modalPlainBackgroundColor
        self.historyFrameLeftOverlayNode.backgroundColor = self.hasAnyHistoryMessages == true ? self.presentationData.theme.list.modalBlocksBackgroundColor : self.presentationData.theme.list.modalPlainBackgroundColor
        self.historyFrameRightOverlayNode.backgroundColor = self.hasAnyHistoryMessages == true ? self.presentationData.theme.list.modalBlocksBackgroundColor : self.presentationData.theme.list.modalPlainBackgroundColor
        self.historyFrameTopOverlayNode.backgroundColor = self.hasAnyHistoryMessages == true ? self.presentationData.theme.list.modalBlocksBackgroundColor : self.presentationData.theme.list.modalPlainBackgroundColor
        context.setFillColor(theme.list.modalBlocksBackgroundColor.cgColor)
}
'''

    def test_transform_keeps_native_owners_and_only_softens_material(self):
        result = self.patch.apply_native_material(self.official_fixture())
        self.assertEqual(result.count(self.patch.MARKER), 1)
        self.assertIn("OverlayAudioPlayerControlsNode(", result)
        self.assertIn("ChatHistoryListNodeImpl(", result)
        self.assertIn("systemStyle: .glass", result)
        self.assertIn("UIVisualEffectView()", result)
        self.assertIn("UIColor(white: 0.0, alpha: 0.18)", result)
        self.assertNotIn("UIColor(white: 0.0, alpha: 0.5)", result)

        # Exact bounded material coverage:
        #   4 initial surfaces
        # + 2 branches on historyBackgroundContentNode refresh
        # + 6 branches on the three frame-overlay refreshes
        # + 1 native corner fill
        # = 13 alpha applications. This is not a global replacement; every
        # source anchor is independently fail-closed in apply_native_material().
        self.assertEqual(result.count("withAlphaComponent(0.94)"), 13)

    def test_transform_fails_closed_when_native_anchor_changes(self):
        fixture = self.official_fixture().replace(
            "        self.dimNode.backgroundColor = UIColor(white: 0.0, alpha: 0.5)\n",
            "",
        )
        with self.assertRaises(RuntimeError):
            self.patch.apply_native_material(fixture)

    def test_transform_does_not_add_fake_profile_or_second_player(self):
        result = self.patch.apply_native_material(self.official_fixture())
        for token in (
            "GhostBaseMusicProfileBackdropView",
            "snapshotView(",
            "AVPlayer(",
            "UniversalVideoNode(",
            "CADisplayLink(",
            "CIImage(",
        ):
            self.assertNotIn(token, result)

    def test_verifier_contract_exists(self):
        verifier = self.load(VERIFY, "build133_music_verify_test")
        self.assertTrue(callable(verifier.main))


if __name__ == "__main__":
    unittest.main()
