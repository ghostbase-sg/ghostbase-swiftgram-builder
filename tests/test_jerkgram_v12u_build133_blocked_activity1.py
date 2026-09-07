import importlib.util
import inspect
from pathlib import Path
import sys
import unittest


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts" / "apply_jerkgram_v12u_build133_blocked_activity1.py"
PATCH2 = REPO / "scripts" / "apply_jerkgram_v12u_build133_blocked_activity2.py"
VERIFY = REPO / "scripts" / "verify_jerkgram_v12u_build133_blocked_activity1.py"


class Build133BlockedActivityContracts(unittest.TestCase):
    @staticmethod
    def load(path: Path, name: str):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def setUp(self):
        self.patch = self.load(PATCH, "build133_blocked_activity_patch")

    def test_only_blocked_mention_has_no_target(self):
        targets = [(1, "A", True)]
        self.assertIsNone(self.patch.visible_navigation_target(targets, {"A"}, enabled=True))

    def test_blocked_then_allowed_targets_allowed(self):
        targets = [(1, "A", True), (2, "B", True)]
        self.assertEqual(self.patch.visible_navigation_target(targets, {"A"}, enabled=True), 2)

    def test_removed_message_is_not_navigable(self):
        targets = [(1, "B", False), (2, "C", True)]
        self.assertEqual(self.patch.visible_navigation_target(targets, set(), enabled=True), 2)

    def test_feature_off_preserves_stock_first_existing_target(self):
        targets = [(1, "A", True), (2, "B", True)]
        self.assertEqual(self.patch.visible_navigation_target(targets, {"A"}, enabled=False), 1)

    def test_unknown_actor_is_preserved(self):
        targets = [(1, None, True)]
        self.assertEqual(self.patch.visible_navigation_target(targets, {"A"}, enabled=True), 1)

    def test_private_chat_navigation_and_activity_remain_stock(self):
        self.assertIn("chat_kind", inspect.signature(self.patch.visible_navigation_target).parameters)
        self.assertIn("chat_kind", inspect.signature(self.patch.visible_activity).parameters)
        self.assertEqual(
            self.patch.visible_navigation_target(
                [(1, "A", True)], {"A"}, enabled=True, chat_kind="private"
            ),
            1,
        )
        self.assertTrue(
            self.patch.visible_activity(
                stock=True,
                summary_count=1,
                loaded=[("A", True)],
                blocked={"A"},
                enabled=True,
                chat_kind="private",
            )
        )

    def test_chat_history_removes_blocked_authors_when_enabled(self):
        self.assertTrue(callable(getattr(self.patch, "visible_chat_messages", None)))
        messages = [(1, "A"), (2, "B"), (3, "ME")]
        self.assertEqual(
            self.patch.visible_chat_messages(messages, {"A"}, account="ME", enabled=True),
            [(2, "B"), (3, "ME")],
        )

    def test_chat_history_preserves_messages_when_disabled(self):
        self.assertTrue(callable(getattr(self.patch, "visible_chat_messages", None)))
        messages = [(1, "A"), (2, "B")]
        self.assertEqual(
            self.patch.visible_chat_messages(messages, {"A"}, account="ME", enabled=False),
            messages,
        )

    def test_chat_history_never_filters_private_or_broadcast_chats(self):
        messages = [(1, "A"), (2, "B")]
        self.assertIn(
            "chat_kind",
            inspect.signature(self.patch.visible_chat_messages).parameters,
            "chat history scope is not explicit",
        )
        self.assertEqual(
            self.patch.visible_chat_messages(
                messages, {"A"}, account="ME", enabled=True, chat_kind="private"
            ),
            messages,
        )
        self.assertEqual(
            self.patch.visible_chat_messages(
                messages, {"A"}, account="ME", enabled=True, chat_kind="channel"
            ),
            messages,
        )

    def test_chat_history_source_filters_before_building_entries(self):
        fixture = '''loop: for entry in view.entries {
        var message = entry.message
        var isRead = entry.isRead

        if pendingRemovedMessages.contains(message.id) {
            continue
        }

        count += 1
    }
'''
        patch_entries = getattr(self.patch, "patch_chat_history_entries", None)
        if not callable(patch_entries):
            self.fail("chat history entry owner is not patchable")
        updated = patch_entries(fixture)
        self.assertIn("JerkgramBlockedReactionPolicy.isMessageHidden(", updated)
        self.assertLess(updated.index("JerkgramBlockedReactionPolicy.isMessageHidden("), updated.index("count += 1"))

    def test_chat_history_reacts_to_block_list_and_setting_changes(self):
        fixture = '''        let historyViewUpdateValue = historyViewUpdate
        historyViewUpdate = stopHistoryViewUpdates |> mapToSignal { value in
'''
        patch_list = getattr(self.patch, "patch_chat_history_list", None)
        if not callable(patch_list):
            self.fail("chat history update stream is not patchable")
        updated = patch_list(fixture)
        self.assertIn("JerkgramBlockedReactionPolicy.presentationUpdates", updated)
        self.assertIn("combineLatest(", updated)

    def test_chat_list_activity_hidden_when_complete_set_is_blocked(self):
        self.assertFalse(
            self.patch.visible_activity(
                stock=True,
                summary_count=1,
                loaded=[("A", True)],
                blocked={"A"},
                enabled=True,
            )
        )

    def test_chat_list_activity_preserved_when_allowed_exists(self):
        self.assertTrue(
            self.patch.visible_activity(
                stock=True,
                summary_count=2,
                loaded=[("A", True), ("B", True)],
                blocked={"A"},
                enabled=True,
            )
        )

    def test_chat_list_activity_hides_stale_summary_if_loaded_targets_are_blocked(self):
        self.assertFalse(
            self.patch.visible_activity(
                stock=True,
                summary_count=2,
                loaded=[("A", True)],
                blocked={"A"},
                enabled=True,
            )
        )

    def test_materialized_delete_owners_allow_different_indentation(self):
        sys.path.insert(0, str(REPO / "scripts"))
        try:
            patch2 = self.load(PATCH2, "build133_blocked_activity_patch2")
        finally:
            sys.path.pop(0)

        def owner(signature: str, indent: str) -> str:
            return f'''{signature} {{
{indent}var tags = currentMessage.tags
{indent}if attributes.contains(where: {{ ($0 as? ReactionsMessageAttribute)?.hasUnseen == true }}) {{
{indent}    tags.insert(.unseenReaction)
{indent}}} else {{
{indent}    tags.remove(.unseenReaction)
{indent}}}
}}
'''

        fixture = (
            owner(
                "func _internal_deleteAllReactionsWithAuthor(account: Account, peerId: PeerId, authorId: PeerId, aroundMessageId: MessageId?) -> Signal<Never, NoError>",
                "                    ",
            )
            + "\n"
            + owner(
                "func _internal_deleteReaction(account: Account, messageId: MessageId, authorId: PeerId) -> Signal<Never, NoError>",
                "                ",
            )
            + "\nfunc _internal_clearHistory() {}\n"
        )
        result = patch2.patch_delete_messages(fixture)
        self.assertEqual(result.count(patch2.base.DELETE_MARKER), 2)
        self.assertNotIn("?.hasUnseen == true", result)
        # Each owner contains the local variable name, policy call and if-check.
        self.assertEqual(result.count("hasVisibleUnseenReaction"), 6)

    def test_verifier_contract_exists(self):
        verify = self.load(VERIFY, "build133_blocked_activity_verify")
        self.assertTrue(callable(verify.verify_chat_list_owner))
        self.assertTrue(callable(verify.verify_navigation_owner))


if __name__ == "__main__":
    unittest.main()
