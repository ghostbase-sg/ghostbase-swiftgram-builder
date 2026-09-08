import importlib.util
from pathlib import Path
import sys
import unittest


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts/apply_jerkgram_v12zb_build135_visibility_runtime1.py"


def load_patch():
    if not PATCH.is_file():
        return None
    sys.path.insert(0, str(REPO / "scripts"))
    spec = importlib.util.spec_from_file_location("build135_visibility_runtime", PATCH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class Build135VisibilityRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = load_patch()

    def test_build135_patch_exists(self):
        self.assertIsNotNone(self.patch)

    def test_chat_list_falls_back_to_previous_visible_message(self):
        self.assertEqual(
            self.patch.visible_preview(
                [(103, 7), (102, 7), (101, 9)],
                blocked={7},
                account=1,
                chat_kind="supergroup",
            ),
            (101, 9),
        )

    def test_private_chat_is_never_filtered(self):
        self.assertEqual(
            self.patch.visible_preview(
                [(103, 7), (102, 9)],
                blocked={7},
                account=1,
                chat_kind="private",
            ),
            (103, 7),
        )

    def test_unread_badge_subtracts_only_hidden_unread_messages(self):
        entries = [
            (7, False),
            (7, False),
            (9, False),
            (7, True),
        ]
        self.assertEqual(
            self.patch.visible_unread_count(
                3,
                entries,
                blocked={7},
                account=1,
                chat_kind="group",
            ),
            1,
        )

    def test_account_projection_clears_previous_runtime_value(self):
        defaults = {
            "jerkgram.GhostMode.ScheduledSend": True,
            "jerkgram.account.100.setting.jerkgram.GhostMode.ScheduledSend": True,
            "jerkgram.account.200.setting.jerkgram.GhostMode.ReadMessages": False,
        }
        projected = self.patch.project_account_settings(defaults, account_peer_id=200)
        self.assertNotIn("jerkgram.GhostMode.ScheduledSend", projected)
        self.assertFalse(projected["jerkgram.GhostMode.ReadMessages"])

    def test_owner_patches_are_group_scoped_and_live(self):
        chat_list = self.patch.patch_chat_list_location(
            "import Foundation\n\npublic func chatListViewForLocation("
        )
        self.assertIn("BUILD135_VISIBLE_CHAT_LIST1", chat_list)
        self.assertIn("JerkgramBlockedReactionPolicy.isGroupChat", chat_list)
        self.assertIn("getMessagesHistoryViewState", chat_list)
        self.assertIn("withUpdatedCommunitySummary", chat_list)

        chat = self.patch.patch_chat_unread(
            "import Foundation\n\n    func setupChatHistoryNode(historyNode: ChatHistoryListNodeImpl) {\n"
            "                let throttledUnreadCountSignal = self.context.chatLocationUnreadCount(for: self.chatLocation, contextHolder: self.chatLocationContextHolder)\n"
            "                |> mapToThrottled { value -> Signal<Int, NoError> in\n"
        )
        self.assertIn("BUILD135_VISIBLE_UNREAD1", chat)
        self.assertIn("presentationUpdates", chat)
        self.assertIn("isGroupChat", chat)

    def test_account_switch_projects_before_current_id_changes(self):
        source = (
            "import Foundation\n"
            "public final class SharedAccountContext {\n"
            "    public func switchToAccount(id: AccountRecordId, fromSettingsController settingsController: ViewController? = nil, withChatListController chatListController: ViewController? = nil) {\n"
            "        if self.activeAccountsValue?.primary?.account.id == id {\n"
            "            return\n"
            "        }\n"
            "        let _ = self.accountManager.transaction({ transaction -> Bool in\n"
            "            if transaction.getCurrent()?.0 != id {\n"
            "                transaction.setCurrentId(id)\n"
            "                return true\n"
            "            } else {\n"
            "                return false\n"
            "            }\n"
            "        }).start()\n"
            "    }\n"
            "}\n"
        )
        updated = self.patch.patch_shared_account_context(source)
        projection = updated.index("jerkgramBuild135ProjectAccountSettings")
        mutation = updated.index("transaction.setCurrentId(id)")
        self.assertLess(projection, mutation)


if __name__ == "__main__":
    unittest.main()
