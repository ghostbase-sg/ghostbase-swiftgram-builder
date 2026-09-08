#!/usr/bin/env python3

from pathlib import Path
import os

import apply_jerkgram_v12zb_build135_visibility_runtime1 as patch


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build135 visibility/runtime verify] " + message)


def main() -> None:
    chat_list = patch.CHAT_LIST_LOCATION.read_text(encoding="utf-8")
    chat_unread = patch.CHAT_UNREAD.read_text(encoding="utf-8")
    accounts = patch.SHARED_ACCOUNT_CONTEXT.read_text(encoding="utf-8")

    require(chat_list.count(patch.CHAT_LIST_MARKER) == 1, "chat-list owner")
    require(chat_list.count("jerkgramBuild135VisibleChatListUpdate(account: account, update: summarized)") == 3, "all chat-list locations")
    require("historyView.entries.reversed().first" in chat_list, "previous visible preview fallback")
    require("jerkgramBuild135ReadCounters" in chat_list, "chat-list unread count owner")
    require("JerkgramBlockedReactionPolicy.isGroupChat" in chat_list, "group-only chat-list gate")

    require(chat_unread.count(patch.CHAT_UNREAD_MARKER) == 1, "in-chat unread owner")
    require("JerkgramBlockedReactionPolicy.presentationUpdates" in chat_unread, "live visibility refresh")
    require("return max(0, stockCount - hiddenUnreadCount)" in chat_unread, "hidden unread subtraction")
    require("JerkgramBlockedReactionPolicy.isGroupChat" in chat_unread, "group-only in-chat gate")

    require(accounts.count(patch.ACCOUNT_MARKER) == 1, "account runtime owner")
    require(accounts.count("jerkgramBuild135ProjectAccountSettings(accountPeerId:") >= 3, "initial and switched account projection")
    require(accounts.index("jerkgramBuild135ProjectAccountSettings(accountPeerId: target.account.peerId.toInt64())") < accounts.index("transaction.setCurrentId(id)"), "projection precedes account mutation")
    require("sharedDefaults.removeObject(forKey: scheduledSendKey)" in accounts, "stale scheduled-send runtime clearing")

    print("[Build135 visibility/runtime verify] PREFLIGHT GREEN")
    print("[Build135 visibility/runtime verify] group-only previous preview + visible unread counts + synchronous account settings")


if __name__ == "__main__":
    main()
