import importlib.util
from pathlib import Path
import sys
import unittest


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts/apply_jerkgram_v12zc_build136_visible_order_cache1.py"


def load_patch():
    if not PATCH.is_file():
        return None
    sys.path.insert(0, str(REPO / "scripts"))
    spec = importlib.util.spec_from_file_location("build136_visible_order_cache", PATCH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class Build136VisibleOrderCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = load_patch()

    def test_build136_patch_exists(self):
        self.assertIsNotNone(self.patch)

    def test_hidden_top_message_uses_fallback_only_for_presentation_order(self):
        self.assertEqual(
            self.patch.presentation_sort_index(
                source_index=300,
                visible_message_index=120,
                pinned=False,
            ),
            120,
        )
        self.assertEqual(
            self.patch.navigation_index(source_index=300),
            300,
        )

    def test_pinned_chat_keeps_telegram_order(self):
        self.assertEqual(
            self.patch.presentation_sort_index(
                source_index=300,
                visible_message_index=120,
                pinned=True,
            ),
            300,
        )

    def test_normal_preview_or_album_keeps_telegram_order(self):
        self.assertEqual(
            self.patch.presentation_sort_index(
                source_index=300,
                visible_message_index=120,
                pinned=False,
                is_fallback=False,
            ),
            300,
        )

    def test_unchanged_visibility_signature_reuses_cached_history_result(self):
        signature = self.patch.visibility_signature(
            source_index=300,
            stock_unread=4,
            blocked_revision=8,
            enabled=True,
        )
        self.assertFalse(self.patch.needs_history_scan(signature, signature))

    def test_cache_invalidates_for_message_read_policy_or_blocked_list_change(self):
        baseline = self.patch.visibility_signature(300, 4, 8, True)
        changed = [
            self.patch.visibility_signature(301, 4, 8, True),
            self.patch.visibility_signature(300, 3, 8, True),
            self.patch.visibility_signature(300, 4, 9, True),
            self.patch.visibility_signature(300, 4, 8, False),
        ]
        for candidate in changed:
            with self.subTest(candidate=candidate):
                self.assertTrue(self.patch.needs_history_scan(baseline, candidate))

    def test_chat_list_entry_keeps_source_index_and_has_separate_sort_index(self):
        source = '''
enum ChatListNodeEntry {
    struct PeerEntryData: Equatable {
        var index: EngineChatList.Item.Index
        var messages: [EngineMessage]
    }

    struct ContactEntryData: Equatable {
        var peer: EnginePeer
    }

    var sortIndex: ChatListNodeEntrySortIndex {
        switch self {
        case let .PeerEntry(peerEntry):
            return .index(peerEntry.index)
        default:
            fatalError()
        }
    }
}

func chatListNodeEntriesForView(accountPeerId: EnginePeer.Id, entry: EngineChatList.Item, pinnedIndexOffset: UInt16) {
    let value = ChatListNodeEntry.PeerEntryData(
        index: offsetPinnedIndex(entry.index, offset: pinnedIndexOffset),
        presentationData: state.presentationData,
        messages: entry.messages
    )
}
'''
        updated = self.patch.patch_chat_list_entries(source)
        self.assertIn("var jerkgramBuild136PresentationSortIndex", updated)
        self.assertIn("return .index(peerEntry.jerkgramBuild136PresentationSortIndex ?? peerEntry.index)", updated)
        self.assertIn("var index: EngineChatList.Item.Index", updated)
        self.assertIn("jerkgramBuild136PresentationSortIndex: entry.jerkgramPresentationIndex", updated)

    def test_presentation_items_are_sorted_with_the_explicit_override(self):
        self.assertIn("}.sorted { lhs, rhs in", self.patch.CHAT_LIST_HELPER)
        self.assertIn("lhs.jerkgramPresentationIndex ?? lhs.index", self.patch.CHAT_LIST_HELPER)

    def test_fallback_refreshes_for_history_mutations_without_a_timer(self):
        self.assertTrue(self.patch.should_refresh_fallback(item_was_empty=True, update_kind="generic"))
        self.assertTrue(self.patch.should_refresh_fallback(item_was_empty=True, update_kind="fill_hole"))
        self.assertFalse(self.patch.should_refresh_fallback(item_was_empty=True, update_kind="update_visible"))
        self.assertFalse(self.patch.should_refresh_fallback(item_was_empty=False, update_kind="generic"))
        self.assertNotIn("createdAt", self.patch.CHAT_LIST_HELPER)

    def test_presentation_index_is_carried_by_the_immutable_engine_item(self):
        source = '''
public final class EngineChatList {
    public final class Item: Equatable {
        public enum Index: Equatable {}
        public let index: Index
        public let messages: [EngineMessage]
        public init(
            index: Index,
            mediaDraftContentType: EngineChatList.MediaDraftContentType?
        ) {
            self.index = index
            self.messages = messages
        }
        public static func ==(lhs: Item, rhs: Item) -> Bool {
            if lhs.index != rhs.index {
                return false
            }
            return true
        }
    }
}
public extension EngineChatList.Item {
    func withUpdatedCommunitySummary(messages: [EngineMessage], readCounters: EnginePeerReadCounters?) -> EngineChatList.Item {
        return EngineChatList.Item(
            index: self.index,
            mediaDraftContentType: self.mediaDraftContentType
        )
    }
}
'''
        updated = self.patch.patch_engine_chat_list(source)
        self.assertIn("public let jerkgramPresentationIndex: Index?", updated)
        self.assertIn("jerkgramPresentationIndex: Index? = nil", updated)
        self.assertIn("self.jerkgramPresentationIndex = jerkgramPresentationIndex", updated)
        self.assertIn("jerkgramPresentationIndex: jerkgramPresentationIndex", updated)

    def test_nil_or_loading_fallback_is_not_cached(self):
        self.assertFalse(self.patch.should_cache_result(item_was_empty=True, fallback_present=False, history_loading=False))
        self.assertFalse(self.patch.should_cache_result(item_was_empty=True, fallback_present=True, history_loading=True))
        self.assertTrue(self.patch.should_cache_result(item_was_empty=True, fallback_present=True, history_loading=False))
        self.assertTrue(self.patch.should_cache_result(item_was_empty=False, fallback_present=False, history_loading=False))

    def test_policy_exposes_revision_without_exposing_mutation(self):
        source = '''
public enum JerkgramBlockedReactionPolicy {
    private static let presentationRevision = Atomic(value: Int32(0))
    private static let presentationRevisionPromise = ValuePromise<Int32>(0, ignoreRepeated: false)

    public static var presentationUpdates: Signal<Int32, NoError> {
        return self.presentationRevisionPromise.get()
    }
}
'''
        updated = self.patch.patch_policy(source)
        self.assertIn("public static var presentationRevisionValue: Int32", updated)
        self.assertIn("return self.presentationRevision.with", updated)

    def test_account_projection_uses_materialized_key_list_without_forced_sync(self):
        source = '''
// MARK: Jerkgram v1.2ZB BUILD135_ACCOUNT_RUNTIME1
private func jerkgramBuild135ProjectAccountSettings(accountPeerId: Int64) {
    let defaults = UserDefaults.standard
    let marker = ".setting."
    let targetPrefix = "jerkgram.account.\\(accountPeerId).setting."
    var suffixes = Set<String>()
    for key in defaults.dictionaryRepresentation().keys where key.hasPrefix("jerkgram.account.") {
        if let range = key.range(of: marker) {
            suffixes.insert(String(key[range.upperBound...]))
        }
    }
    for suffix in suffixes {
        let scopedKey = targetPrefix + suffix
        if let value = defaults.object(forKey: scopedKey) {
            defaults.set(value, forKey: suffix)
        } else {
            defaults.removeObject(forKey: suffix)
        }
    }
    defaults.synchronize()
}

public final class SharedAccountContext {}
'''
        updated = self.patch.patch_account_context(
            source,
            runtime_keys=["jerkgram.GhostMode.ScheduledSend", "jerkgram.Messages.HideBlockedMessages"],
        )
        self.assertNotIn("dictionaryRepresentation()", updated)
        self.assertNotIn("synchronize()", updated)
        self.assertIn('"jerkgram.GhostMode.ScheduledSend"', updated)
        self.assertIn('"jerkgram.Messages.HideBlockedMessages"', updated)

    def test_runtime_key_extraction_follows_account_state_map_only(self):
        settings = '''
private enum GhostBaseKey {
    static let scheduledSend = "jerkgram.GhostMode.ScheduledSend"
    static let unrelated = "jerkgram.Unrelated.GlobalOnly"
}
private let sendStyleKey =
    "jerkgram.Messages.SendTextStyle"
private func jerkgramStateValues(_ state: GhostBaseSettingsState) -> [String: JerkgramSettingValue] {
    return [
        GhostBaseKey.scheduledSend: .bool(state.scheduledSend),
        sendStyleKey: .string(state.sendStyle)
    ]
}

private func jerkgramPersistChangedSettings() {}
'''
        self.assertEqual(
            self.patch.extract_runtime_keys(settings),
            ["jerkgram.GhostMode.ScheduledSend", "jerkgram.Messages.SendTextStyle"],
        )


if __name__ == "__main__":
    unittest.main()
