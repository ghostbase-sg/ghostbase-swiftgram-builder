#!/usr/bin/env python3

from pathlib import Path
import os

import apply_jerkgram_v12zc_build136_visible_order_cache1 as patch


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build136 visible order/cache verify] " + message)


def main() -> None:
    chat_list = patch.CHAT_LIST_LOCATION.read_text(encoding="utf-8")
    entries = patch.CHAT_LIST_ENTRIES.read_text(encoding="utf-8")
    engine_chat_list = patch.ENGINE_CHAT_LIST.read_text(encoding="utf-8")
    policy = patch.REACTION_POLICY.read_text(encoding="utf-8")
    accounts = patch.SHARED_ACCOUNT_CONTEXT.read_text(encoding="utf-8")

    require(policy.count(patch.POLICY_MARKER) == 1, "read-only presentation revision owner")
    require("public static var presentationRevisionValue: Int32" in policy, "presentation revision accessor")
    require(chat_list.count(patch.CHAT_LIST_MARKER) == 1, "chat-list cache owner")
    require(chat_list.count("jerkgramBuild136VisibleChatListUpdate(account: account, update: summarized)") == 3, "all chat-list flows")
    require("jerkgramBuild135VisibleChatListUpdate" not in chat_list, "uncached Build135 chat-list helper survived")
    require("cached.sourceIndex == item.index" in chat_list, "top-message cache signature")
    require("cached.stockUnreadCount == stockUnreadCount" in chat_list, "read-state cache signature")
    require("cached.presentationRevision == presentationRevision" in chat_list, "policy revision cache signature")
    require("let blockedPeerIds:" not in chat_list, "blocked set must not be duplicated in cache entries")
    require("guard !missingPeerIds.isEmpty else" in chat_list, "no-transaction cache-hit path")
    require("index.pinningIndex == nil" in chat_list, "pinned order guard")
    require("jerkgramBuild136VisibilityCacheLimit = 256" in chat_list, "bounded visibility cache")
    require("jerkgramBuild136ClearVisibilityCache(accountPeerId:" in chat_list, "disabled/empty cache clear")
    require("case .Generic, .FillHole:" in chat_list, "edit/delete/hole fallback invalidation")
    require("if historyView.isLoading" in chat_list, "loading fallback guard")
    require("}.sorted { lhs, rhs in" in chat_list, "presentation EngineChatList must be sorted")
    require("removing: removedCacheKeys" in chat_list, "incomplete cache entries must be removed")
    require("lhs.jerkgramPresentationIndex ?? lhs.index" in chat_list, "immutable payload owns presentation sorting")

    require(engine_chat_list.count(patch.ENGINE_ITEM_MARKER) == 1, "immutable EngineChatList presentation payload")
    require("public let jerkgramPresentationIndex: Index?" in engine_chat_list, "optional presentation index field")
    require("self.jerkgramPresentationIndex = jerkgramPresentationIndex" in engine_chat_list, "presentation init assignment")
    require("lhs.jerkgramPresentationIndex != rhs.jerkgramPresentationIndex" in engine_chat_list, "presentation equality")
    require("jerkgramPresentationIndex: jerkgramPresentationIndex" in engine_chat_list, "community summary propagation")

    require(entries.count(patch.ENTRY_MARKER) == 1, "presentation sort-index owner")
    require("return .index(peerEntry.jerkgramBuild136PresentationSortIndex ?? peerEntry.index)" in entries, "row sort uses explicit visible index")
    require("jerkgramBuild136PresentationSortIndex: entry.jerkgramPresentationIndex" in entries, "entry consumes immutable presentation payload")
    require("var index: EngineChatList.Item.Index" in entries, "Telegram source index retained")

    account_start = accounts.index(patch.ACCOUNT_MARKER)
    account_end = accounts.index("\npublic final class SharedAccountContext", account_start)
    helper = accounts[account_start:account_end]
    require("dictionaryRepresentation()" not in helper, "full defaults scan survived")
    require("synchronize()" not in helper, "forced defaults synchronization survived")
    require('"jerkgram.GhostMode.ScheduledSend"' in helper, "Scheduled Send projection missing")
    require('UserDefaults(suiteName: "group.4a348a9b186b700c.1")' in helper, "Share Extension projection missing")

    print("[Build136 visible order/cache verify] PREFLIGHT GREEN")
    print("[Build136 visible order/cache verify] stable source navigation + visible ordering + cache-hit fast path + bounded account projection")


if __name__ == "__main__":
    main()
