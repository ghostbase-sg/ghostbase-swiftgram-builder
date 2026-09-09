import importlib.util
from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))


class Performance2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = REPO / "scripts/apply_jerkgram_build137_performance2.py"
        cls.patch = None
        if path.exists():
            spec = importlib.util.spec_from_file_location("performance2", path)
            cls.patch = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.patch)

    def test_rewrites_only_supported_reads_and_preserves_defaults_and_writes(self):
        self.assertIsNotNone(self.patch, "performance2 overlay is missing")
        source = """let a = (UserDefaults.standard.object(forKey: "jerkgram.ProtectedContent.Enabled") as? Bool) ?? true
let b = UserDefaults.standard.string(
    forKey: "jerkgram.Messages.SendTextStyle"
) ?? "normal"
UserDefaults.standard.set(false, forKey: "jerkgram.ProtectedContent.Enabled")
let c = UserDefaults.standard.object(forKey: "unrelated")
"""
        actual = self.patch.patch_reads(source)
        self.assertIn('(JerkgramHotSettings.object(forKey: "jerkgram.ProtectedContent.Enabled") as? Bool) ?? true', actual)
        self.assertIn('(JerkgramHotSettings.object(forKey: "jerkgram.Messages.SendTextStyle") as? String) ?? "normal"', actual)
        self.assertIn('UserDefaults.standard.set(false,', actual)
        self.assertIn('UserDefaults.standard.object(forKey: "unrelated")', actual)
        self.assertEqual(actual, self.patch.patch_reads(actual))

    def test_multiline_diagnostics_are_removed_without_removing_send_logic(self):
        self.assertIsNotNone(self.patch, "performance2 overlay is missing")
        source = """enqueue(messages)
UserDefaults.standard.set(
    UserDefaults.standard.integer(forKey: "jerkgram.V10T.SendTextStyleApplied.Count") + 1,
    forKey: "jerkgram.V10T.SendTextStyleApplied.Count"
)
UserDefaults.standard.set(true, forKey: "jerkgram.ProtectedContent.Enabled")
return messages
"""
        actual = self.patch.strip_diagnostics(source)
        self.assertNotIn("SendTextStyleApplied.Count", actual)
        self.assertIn("enqueue(messages)", actual)
        self.assertIn('set(true, forKey: "jerkgram.ProtectedContent.Enabled")', actual)
        self.assertIn("return messages", actual)

    def test_projection_refresh_is_at_exit_after_early_return_and_writes(self):
        self.assertIsNotNone(self.patch, "performance2 overlay is missing")
        source = """private func project() {
    guard enabled else { return }
    defaults.set(value, forKey: key)
}
"""
        actual = self.patch.refresh_at_exit(source, "private func project(")
        self.assertIn("defer { JerkgramHotSettings.invalidate() }", actual)
        self.assertLess(actual.index("defer"), actual.index("guard"))
        self.assertEqual(actual, self.patch.refresh_at_exit(actual, "private func project("))

    def test_settings_sync_set_includes_all_snapshot_keys(self):
        self.assertIsNotNone(self.patch, "performance2 overlay is missing")
        source = """private func jerkgramPersistChangedSettings() {
    let jerkgramSynchronousRuntimeSettingKeys: Set<String> = [
        GhostBaseKey.scheduledSend,
    ]
    writeSettings()
}
"""
        actual = self.patch.patch_settings(source)
        self.assertIn("Set<String>([", actual)
        self.assertIn("]).union(JerkgramHotSettings.keys)", actual)
        self.assertNotIn("\n    ].union(JerkgramHotSettings.keys)", actual)
        self.assertEqual(actual, self.patch.patch_settings(actual))

    def test_readstats_keeps_results_and_removes_empty_diagnostic_bindings(self):
        self.assertIsNotNone(self.patch, "performance2 overlay is missing")
        source = """if let first = items.first {
    UserDefaults.standard.set(first.0, forKey: "jerkgram.READ3.FirstUserId")
}
if items.isEmpty {
    UserDefaults.standard.set("EMPTY", forKey: "jerkgram.READ3.FinalVerdict")
} else {
    UserDefaults.standard.set("OK", forKey: "jerkgram.READ3.FinalVerdict")
}
return items
"""
        actual = self.patch.strip_diagnostics(source)
        self.assertNotIn("if let first", actual)
        self.assertNotIn("if items.isEmpty", actual)
        self.assertIn("return items", actual)

    def test_activity_load_and_publication_share_invalidation_lock(self):
        source = self.patch.base.ACTIVITY_RUNTIME
        actual = self.patch.patch_activity_lock(source)
        block = self.patch.base.function_block(actual, "private static func settings()")
        self.assertNotIn("cached.with", block)
        self.assertLess(block.index("cached.modify"), block.index("UserDefaults.standard"))
        self.assertEqual(actual, self.patch.patch_activity_lock(actual))

    def test_history_mutations_cannot_reuse_fallback(self):
        source = self.patch.base.patch_chat_list_helper(self.patch.base.CHAT_LIST_FIXTURE)
        actual = self.patch.restore_history_invalidation(source)
        self.assertIn("case .Generic, .FillHole:", actual)
        self.assertIn("!mustRefreshFallback", actual)
        self.assertLess(actual.index("let mustRefreshFallback"), actual.index("if let cached"))
        self.assertEqual(actual, self.patch.restore_history_invalidation(actual))

    def test_projection_refreshes_all_runtime_consumers(self):
        source = "private func project() { defaults.set(value, forKey: key) }"
        actual = self.patch.refresh_projection(source, "private func project(")
        for call in ("JerkgramHotSettings.invalidate()", "JerkgramActivityGhostRuntime.invalidate()",
                     "GhostBaseGlassStyle.reloadFromDefaults()", self.patch.base.RAM_NOTIFICATION):
            self.assertIn(call, actual)
        self.assertIn("Queue.mainQueue().async", actual)
        self.assertEqual(actual, self.patch.refresh_projection(actual, "private func project("))

    def test_ci_runs_phase_two_after_phase_one_and_before_music(self):
        installer = (REPO / "scripts/install_jerkgram_v12w_build133_probe_hook.py").read_text()
        workflow = (REPO / ".github/workflows/build.yml").read_text()
        for text in (installer, workflow):
            phase1 = text.index("verify_jerkgram_v12zd_build137_performance1.py")
            apply2 = text.index("apply_jerkgram_build137_performance2.py")
            verify2 = text.index("verify_jerkgram_build137_performance2.py")
            music = text.index("apply_jerkgram_v12w_build133_music_overlay1.py")
            self.assertLess(phase1, apply2)
            self.assertLess(apply2, verify2)
            self.assertLess(verify2, music)


if __name__ == "__main__":
    unittest.main()
