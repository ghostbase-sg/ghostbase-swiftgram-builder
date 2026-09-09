import importlib.util
from pathlib import Path
import sys
import unittest


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts/apply_jerkgram_v12zd_build137_performance1.py"


def load_patch():
    if not PATCH.is_file():
        return None
    sys.path.insert(0, str(REPO / "scripts"))
    spec = importlib.util.spec_from_file_location("build137_performance", PATCH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class Build137PerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = load_patch()

    def test_performance_overlay_exists(self):
        self.assertIsNotNone(self.patch)

    def test_ram_overlay_does_not_subscribe_to_all_defaults_or_measure_in_layout(self):
        source = self.patch.RAM_ROOT_FIXTURE
        updated = self.patch.patch_ram_root(source)
        self.assertNotIn("UserDefaults.didChangeNotification", updated)
        self.assertIn("GhostBaseRamOverlayPreferenceChanged", updated)
        layout = self.patch.function_block(updated, "override public func containerLayoutUpdated(")
        self.assertNotIn("ghostBaseUpdateRamOverlayState()", layout)
        self.assertNotIn("ghostBaseUpdateRamValue()", layout)
        self.assertIn("ghostBaseLayoutRamLabel()", layout)

    def test_root_and_stock_memory_monitors_share_one_off_main_sampler(self):
        app_delegate = self.patch.patch_app_delegate_memory(self.patch.APP_DELEGATE_FIXTURE)
        root = self.patch.patch_ram_root(self.patch.RAM_ROOT_FIXTURE)

        self.assertEqual(1, app_delegate.count("BUILD137_MEMORY_SAMPLER1"))
        self.assertIn('DispatchQueue(label: "jerkgram.memory.sampler", qos: .utility)', app_delegate)
        self.assertIn("private var completions: [String: (Int) -> Void] = [:]", app_delegate)
        self.assertIn('sample(consumer: "appDelegate")', app_delegate)
        self.assertIn("jerkgramMemoryTimer.tolerance = 0.25", app_delegate)
        self.assertNotIn("let value = getMemoryConsumption()", self.patch.function_block(
            app_delegate,
            self.patch.APP_LAUNCH_SIGNATURE,
        ))

        update = self.patch.function_block(root, "private func ghostBaseUpdateRamValue()")
        self.assertIn('sample(consumer: "ramOverlay")', update)
        self.assertNotIn("ghostBaseCurrentMemoryFootprint", root)
        self.assertNotIn("ghostBaseRamMeasurementQueue", root)
        self.assertNotIn("ghostBaseRamMeasurementInFlight", root)
        self.assertIn("timer.tolerance = 0.5", root)

    def test_shared_memory_patch_is_idempotent_and_repairs_duplicate_marker(self):
        once = self.patch.patch_app_delegate_memory(self.patch.APP_DELEGATE_FIXTURE)
        twice = self.patch.patch_app_delegate_memory(once)
        self.assertEqual(once, twice)

        duplicated = once.replace(
            self.patch.MEMORY_SAMPLER_MARKER,
            self.patch.MEMORY_SAMPLER_MARKER + "\n" + self.patch.MEMORY_SAMPLER_MARKER,
            1,
        )
        repaired = self.patch.patch_app_delegate_memory(duplicated)
        self.assertEqual(1, repaired.count(self.patch.MEMORY_SAMPLER_MARKER))

    def test_ram_setting_posts_specific_notification(self):
        updated = self.patch.patch_settings(self.patch.SETTINGS_FIXTURE)
        case = updated[updated.index("case GhostBaseKey.showRamUnderClock:"):]
        self.assertIn("GhostBaseRamOverlayPreferenceChanged", case)

    def test_glass_master_switch_is_cached_in_memory(self):
        updated = self.patch.patch_glass_runtime(self.patch.GLASS_FIXTURE)
        getter = self.patch.property_block(updated, "public static var isEnabled: Bool")
        self.assertNotIn("UserDefaults.standard", getter)
        self.assertIn("enabledLock", getter)
        self.assertIn("enabledValue", getter)
        settings = self.patch.patch_settings(self.patch.SETTINGS_FIXTURE)
        self.assertIn("GhostBaseGlassStyle.setEnabled(value)", settings)

    def test_blocked_policy_reads_defaults_once_per_cache_generation(self):
        updated = self.patch.patch_blocked_policy(self.patch.BLOCKED_POLICY_FIXTURE)
        reactions = self.patch.function_block(updated, "public static func hideBlockedReactions(")
        messages = self.patch.function_block(updated, "public static func hideBlockedMessages(")
        self.assertNotIn("UserDefaults.standard", reactions)
        self.assertNotIn("UserDefaults.standard", messages)
        self.assertIn("settings(accountPeerId:", reactions)
        self.assertIn("settings(accountPeerId:", messages)
        notify = self.patch.function_block(updated, "public static func notifySettingsChanged()")
        self.assertIn("settingsByAccount", notify)

    def test_build136_cache_is_not_forced_to_rescan_unchanged_empty_rows(self):
        updated = self.patch.patch_chat_list_helper(self.patch.CHAT_LIST_FIXTURE)
        self.assertNotIn("mustRefreshFallback", updated)
        self.assertIn("cached.presentationRevision == presentationRevision", updated)

    def test_release_runtime_diagnostics_are_memory_only_noops(self):
        updated = self.patch.patch_runtime_diagnostics(self.patch.DIAGNOSTICS_FIXTURE)
        record = self.patch.function_block(updated, "static func record(_ event: String)")
        self.assertNotIn("queue.async", record)
        self.assertNotIn("UserDefaults.standard", record)
        self.assertIn("_ = event", record)

    def test_legacy_one_time_diagnostic_writes_are_removed_without_changing_gates(self):
        updated = self.patch.strip_legacy_diagnostic_writes(self.patch.ONETIME_FIXTURE)
        self.assertNotIn("OT1.OutgoingKeepBlocked.Count", updated)
        self.assertNotIn("OT1.OutgoingKeepPath", updated)
        self.assertIn("if ghostBaseOT1KeepOutgoingTimerLocal", updated)
        self.assertIn("return .single(true)", updated)

    def test_active_probe_chain_runs_performance_overlay_after_build136_cache(self):
        installer = (REPO / "scripts/install_jerkgram_v12w_build133_probe_hook.py").read_text()
        build136 = installer.index('"verify_jerkgram_v12zc_build136_visible_order_cache1.py"')
        apply = installer.index('"apply_jerkgram_v12zd_build137_performance1.py"')
        verify = installer.index('"verify_jerkgram_v12zd_build137_performance1.py"')
        music = installer.index('"apply_jerkgram_v12w_build133_music_overlay1.py"')
        self.assertLess(build136, apply)
        self.assertLess(apply, verify)
        self.assertLess(verify, music)

    def test_workflow_stages_build137_scripts_and_runs_regression_contract(self):
        workflow = (REPO / ".github/workflows/build.yml").read_text()
        self.assertIn("scripts/apply_jerkgram_v12zd_build137_performance1.py", workflow)
        self.assertIn("scripts/verify_jerkgram_v12zd_build137_performance1.py", workflow)
        self.assertIn("python3 -m unittest tests.test_jerkgram_v12zd_build137_performance1", workflow)

    def test_typing_activity_hot_paths_use_one_cached_snapshot(self):
        account = self.patch.patch_account_activity(self.patch.ACCOUNT_ACTIVITY_FIXTURE)
        upper = self.patch.function_block(account, "public func updateLocalInputActivity(")
        self.assertNotIn("UserDefaults.standard", upper)
        self.assertIn("JerkgramActivityGhostRuntime.shouldSuppress(activity)", upper)
        self.assertIn("BUILD137_ACTIVITY_SNAPSHOT1", account)

        managed = self.patch.patch_managed_activity(self.patch.MANAGED_ACTIVITY_FIXTURE)
        lower = self.patch.function_block(managed, "private func requestActivity(")
        self.assertNotIn("UserDefaults.standard", lower)
        self.assertIn("JerkgramActivityGhostRuntime.shouldSuppress(activity)", lower)

    def test_activity_snapshot_is_invalidated_after_settings_projection(self):
        settings = self.patch.patch_settings(self.patch.SETTINGS_FIXTURE + '''
private func jerkgramPersistChangedSettings(
    accountPeerId: Int64,
    previous: GhostBaseSettingsState?,
    current: GhostBaseSettingsState
) {
    let changes: [String: Value] = [:]
    let jerkgramSynchronousRuntimeSettingKeys: Set<String> = [
        GhostBaseKey.glassEnabled,
    ]
    for key in jerkgramSynchronousRuntimeSettingKeys {
        write(key)
    }
}
''')
        persist = self.patch.function_block(settings, "private func jerkgramPersistChangedSettings(")
        for key in ("typingActions", "recordingActions", "uploadingActions", "stickerActivity", "gameActivity", "emojiActivity"):
            self.assertIn(f"GhostBaseKey.{key}", persist)
        self.assertIn("JerkgramActivityGhostRuntime.invalidate()", persist)

        shared = '''private func jerkgramBuild135ProjectAccountSettings(accountPeerId: Int64) {
    let defaults = UserDefaults.standard
    defaults.set(true, forKey: "jerkgram.GhostMode.TypingActions")
}
'''
        projected = self.patch.patch_shared_account_context(shared)
        self.assertIn("JerkgramActivityGhostRuntime.invalidate()", projected)

    def test_presence_json_work_is_gated_before_decode_and_encode(self):
        updated = self.patch.patch_presence_runtime(self.patch.UPDATE_PEERS_FIXTURE)
        presence = self.patch.function_block(updated, "private func ghostBaseRecordPresence(")
        self.assertIn("shouldRecordTransition", presence)
        self.assertLess(presence.index("shouldRecordTransition"), presence.index("JSONDecoder"))
        user = self.patch.function_block(updated, "private func ghostBaseRegisterKnownUser(")
        self.assertIn("shouldRefreshUser", user)
        self.assertLess(user.index("shouldRefreshUser"), user.index("JSONDecoder"))
        self.assertIn("now - cached.timestamp < 300", updated)
        self.assertIn("private let limit = 4096", updated)

    def test_modern_bounded_presence_store_keeps_cache_and_drops_summary_writes(self):
        source = r'''private enum GhostBasePresenceStoreV11G {
    static let queue = DispatchQueue(label: "jerkgram.PresenceStore.V11G", qos: .utility)
    static let maximumEvents = 500
    static let maximumKnownUsers = 5000
    static let minimumKnownUserWriteInterval: Int64 = 6 * 60 * 60
    private static var histories: [String: [GhostBasePresenceHistoryEvent]] = [:]
    private static var loadedHistoryKeys: Set<String> = []
    private static var loadedKnownUserKeys: Set<String> = []

    static func recordPresence() {
        if let data = try? JSONEncoder().encode(events) {
            defaults.set(data, forKey: key)
            defaults.set(
                "История присутствия: \(events.count) переходов",
                forKey: "jerkgram.Runtime.PresenceSummary.V11G"
            )
        }
    }

    static func registerKnownUser() {
        defaults.set(
            "Известные пользователи: \(ids.count)",
            forKey: "jerkgram.Runtime.KnownUsersSummary.V11G"
        )
    }
}
'''
        updated = self.patch.patch_presence_runtime(source)
        self.assertIn("minimumKnownUserWriteInterval", updated)
        self.assertIn("loadedHistoryKeys", updated)
        self.assertIn("defaults.set(data, forKey: key)", updated)
        self.assertNotIn("PresenceSummary.V11G", updated)
        self.assertNotIn("KnownUsersSummary.V11G", updated)


if __name__ == "__main__":
    unittest.main()
