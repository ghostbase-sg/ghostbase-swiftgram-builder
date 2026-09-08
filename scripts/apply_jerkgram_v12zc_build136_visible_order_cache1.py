#!/usr/bin/env python3

from pathlib import Path
import os
import re


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
CHAT_LIST_LOCATION = ROOT / "submodules/ChatListUI/Sources/Node/ChatListNodeLocation.swift"
CHAT_LIST_ENTRIES = ROOT / "submodules/ChatListUI/Sources/Node/ChatListNodeEntries.swift"
ENGINE_CHAT_LIST = ROOT / "submodules/TelegramCore/Sources/TelegramEngine/Messages/ChatList.swift"
REACTION_POLICY = ROOT / "submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeersContext.swift"
SHARED_ACCOUNT_CONTEXT = ROOT / "submodules/TelegramUI/Sources/SharedAccountContext.swift"
SETTINGS = ROOT / "submodules/SettingsUI/Sources/GhostBase/GhostBaseSettingsController.swift"

CHAT_LIST_MARKER = "// MARK: Jerkgram v1.2ZC BUILD136_VISIBLE_ORDER_CACHE1"
ENTRY_MARKER = "// MARK: Jerkgram v1.2ZC BUILD136_PRESENTATION_SORT_INDEX1"
ENGINE_ITEM_MARKER = "// MARK: Jerkgram v1.2ZC BUILD136_PRESENTATION_PAYLOAD1"
ACCOUNT_MARKER = "// MARK: Jerkgram v1.2ZC BUILD136_ACCOUNT_PROJECTION1"
POLICY_MARKER = "// MARK: Jerkgram v1.2ZC BUILD136_PRESENTATION_REVISION1"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build136 visible order/cache] " + message)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    require(count == 1, f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def presentation_sort_index(source_index, visible_message_index, pinned, is_fallback=True):
    if pinned or not is_fallback or visible_message_index is None:
        return source_index
    return visible_message_index


def navigation_index(source_index):
    return source_index


def visibility_signature(source_index, stock_unread, blocked_revision, enabled):
    return source_index, stock_unread, blocked_revision, enabled


def needs_history_scan(cached_signature, current_signature):
    return cached_signature != current_signature


def should_cache_result(*, item_was_empty, fallback_present, history_loading):
    if history_loading:
        return False
    return not item_was_empty or fallback_present


def should_refresh_fallback(*, item_was_empty, update_kind):
    return item_was_empty and update_kind in ("generic", "fill_hole")


def patch_policy(text: str) -> str:
    if POLICY_MARKER in text:
        require(text.count(POLICY_MARKER) == 1, "policy revision marker is ambiguous")
        return text
    anchor = '''    public static var presentationUpdates: Signal<Int32, NoError> {
        return self.presentationRevisionPromise.get()
    }
'''
    replacement = anchor + '''
    // MARK: Jerkgram v1.2ZC BUILD136_PRESENTATION_REVISION1
    public static var presentationRevisionValue: Int32 {
        return self.presentationRevision.with { value in value }
    }
'''
    return replace_once(text, anchor, replacement, "presentation revision accessor")


CHAT_LIST_HELPER = r'''// MARK: Jerkgram v1.2ZC BUILD136_VISIBLE_ORDER_CACHE1
private struct JerkgramBuild136VisibilityCacheKey: Hashable {
    let accountPeerId: PeerId
    let peerId: PeerId
}

private struct JerkgramBuild136VisibilityCacheEntry {
    let sourceIndex: EngineChatList.Item.Index
    let stockUnreadCount: Int
    let presentationRevision: Int32
    let fallbackMessage: EngineMessage?
    let hiddenUnreadCount: Int32
}

private struct JerkgramBuild136VisibilityCacheState {
    var entries: [JerkgramBuild136VisibilityCacheKey: JerkgramBuild136VisibilityCacheEntry] = [:]
    var insertionOrder: [JerkgramBuild136VisibilityCacheKey] = []
}

private let jerkgramBuild136VisibilityCache = Atomic(
    value: JerkgramBuild136VisibilityCacheState()
)

private let jerkgramBuild136VisibilityCacheLimit = 256

private func jerkgramBuild136ClearVisibilityCache(accountPeerId: PeerId) {
    let _ = jerkgramBuild136VisibilityCache.modify { current in
        var current = current
        let keys = current.entries.keys.filter { key in key.accountPeerId == accountPeerId }
        guard !keys.isEmpty else {
            return current
        }
        let removed = Set(keys)
        for key in keys {
            current.entries.removeValue(forKey: key)
        }
        current.insertionOrder.removeAll(where: { removed.contains($0) })
        return current
    }
}

private func jerkgramBuild136StoreVisibilityCache(
    _ additions: [JerkgramBuild136VisibilityCacheKey: JerkgramBuild136VisibilityCacheEntry],
    removing removals: Set<JerkgramBuild136VisibilityCacheKey>
) {
    guard !additions.isEmpty || !removals.isEmpty else {
        return
    }
    let _ = jerkgramBuild136VisibilityCache.modify { current in
        var current = current
        for key in removals {
            current.entries.removeValue(forKey: key)
        }
        if !removals.isEmpty {
            current.insertionOrder.removeAll(where: { removals.contains($0) })
        }
        for (key, value) in additions {
            if current.entries[key] == nil {
                current.insertionOrder.append(key)
            }
            current.entries[key] = value
        }
        while current.insertionOrder.count > jerkgramBuild136VisibilityCacheLimit {
            let removed = current.insertionOrder.removeFirst()
            current.entries.removeValue(forKey: removed)
        }
        return current
    }
}

private func jerkgramBuild136ReadCounters(
    _ counters: EnginePeerReadCounters?,
    subtracting hiddenUnreadCount: Int32
) -> EnginePeerReadCounters? {
    guard hiddenUnreadCount > 0, let counters, let state = counters._asReadCounters() else {
        return counters
    }
    var remaining = hiddenUnreadCount
    let states = state.states.map { namespace, value -> (MessageId.Namespace, PeerReadState) in
        guard namespace == Namespaces.Message.Cloud, remaining > 0 else {
            return (namespace, value)
        }
        switch value {
        case let .idBased(maxIncomingReadId, maxOutgoingReadId, maxKnownId, count, markedUnread):
            let removed = min(count, remaining)
            remaining -= removed
            return (namespace, .idBased(
                maxIncomingReadId: maxIncomingReadId,
                maxOutgoingReadId: maxOutgoingReadId,
                maxKnownId: maxKnownId,
                count: max(0, count - removed),
                markedUnread: markedUnread
            ))
        case let .indexBased(maxIncomingReadIndex, maxOutgoingReadIndex, count, markedUnread):
            let removed = min(count, remaining)
            remaining -= removed
            return (namespace, .indexBased(
                maxIncomingReadIndex: maxIncomingReadIndex,
                maxOutgoingReadIndex: maxOutgoingReadIndex,
                count: max(0, count - removed),
                markedUnread: markedUnread
            ))
        }
    }
    return EnginePeerReadCounters(state: CombinedPeerReadState(states: states), isMuted: counters.isMuted)
}

private func jerkgramBuild136PresentationIndex(
    sourceIndex: EngineChatList.Item.Index,
    cached: JerkgramBuild136VisibilityCacheEntry?
) -> EngineChatList.Item.Index? {
    guard let cached,
          cached.sourceIndex == sourceIndex,
          let message = cached.fallbackMessage,
          case let .chatList(index) = sourceIndex,
          index.pinningIndex == nil,
          message.id != index.messageIndex.id else {
        return nil
    }
    return .chatList(EngineChatList.Item.Index.ChatList(
        pinningIndex: nil,
        messageIndex: message.index
    ))
}

private func jerkgramBuild136Applying(
    _ cached: JerkgramBuild136VisibilityCacheEntry,
    to item: EngineChatList.Item
) -> EngineChatList.Item {
    var messages = item.messages
    if messages.isEmpty, let fallbackMessage = cached.fallbackMessage {
        messages = [fallbackMessage]
    }
    return item.withUpdatedCommunitySummary(
        messages: messages,
        readCounters: jerkgramBuild136ReadCounters(
            item.readCounters,
            subtracting: cached.hiddenUnreadCount
        ),
        jerkgramPresentationIndex: jerkgramBuild136PresentationIndex(
            sourceIndex: item.index,
            cached: cached
        )
    )
}

private func jerkgramBuild136VisibleChatListUpdate(
    account: Account,
    update: ChatListNodeViewUpdate
) -> Signal<ChatListNodeViewUpdate, NoError> {
    guard JerkgramBlockedReactionPolicy.hideBlockedMessages(accountPeerId: account.peerId) else {
        jerkgramBuild136ClearVisibilityCache(accountPeerId: account.peerId)
        return .single(update)
    }
    let blockedPeerIds = JerkgramBlockedReactionPolicy.blockedPeerIds(accountPeerId: account.peerId)
    guard !blockedPeerIds.isEmpty else {
        jerkgramBuild136ClearVisibilityCache(accountPeerId: account.peerId)
        return .single(update)
    }

    let presentationRevision = JerkgramBlockedReactionPolicy.presentationRevisionValue
    let cachedEntries = jerkgramBuild136VisibilityCache.with { current in current.entries }
    var reusable: [PeerId: JerkgramBuild136VisibilityCacheEntry] = [:]
    var missingPeerIds = Set<PeerId>()
    for item in update.list.items {
        guard case let .chatList(peerId) = item.id,
              let peer = item.renderedPeer.peer,
              JerkgramBlockedReactionPolicy.isGroupChat(peer._asPeer()),
              item.messages.isEmpty || (item.readCounters?.count ?? 0) > 0 else {
            continue
        }
        let key = JerkgramBuild136VisibilityCacheKey(accountPeerId: account.peerId, peerId: peerId)
        let stockUnreadCount = Int(item.readCounters?.count ?? 0)
        let mustRefreshFallback: Bool
        if item.messages.isEmpty {
            switch update.type {
            case .Generic, .FillHole:
                mustRefreshFallback = true
            default:
                mustRefreshFallback = false
            }
        } else {
            mustRefreshFallback = false
        }
        if let cached = cachedEntries[key],
           cached.sourceIndex == item.index,
           cached.stockUnreadCount == stockUnreadCount,
           cached.presentationRevision == presentationRevision,
           !mustRefreshFallback {
            reusable[peerId] = cached
        } else {
            missingPeerIds.insert(peerId)
        }
    }

    let buildUpdate: ([PeerId: JerkgramBuild136VisibilityCacheEntry]) -> ChatListNodeViewUpdate = { resolved in
        let items = update.list.items.map { item -> EngineChatList.Item in
            guard case let .chatList(peerId) = item.id,
                  let cached = resolved[peerId] else {
                return item
            }
            return jerkgramBuild136Applying(cached, to: item)
        }.sorted { lhs, rhs in
            let lhsIndex = lhs.jerkgramPresentationIndex ?? lhs.index
            let rhsIndex = rhs.jerkgramPresentationIndex ?? rhs.index
            return lhsIndex < rhsIndex
        }
        return ChatListNodeViewUpdate(
            list: EngineChatList(
                items: items,
                groupItems: update.list.groupItems,
                additionalItems: update.list.additionalItems,
                hasEarlier: update.list.hasEarlier,
                hasLater: update.list.hasLater,
                isLoading: update.list.isLoading
            ),
            type: update.type,
            scrollPosition: update.scrollPosition
        )
    }

    guard !missingPeerIds.isEmpty else {
        return .single(buildUpdate(reusable))
    }

    return account.postbox.transaction { transaction -> ChatListNodeViewUpdate in
        var resolved = reusable
        var newCacheEntries: [JerkgramBuild136VisibilityCacheKey: JerkgramBuild136VisibilityCacheEntry] = [:]
        var removedCacheKeys = Set<JerkgramBuild136VisibilityCacheKey>()
        for item in update.list.items {
            guard case let .chatList(peerId) = item.id,
                  missingPeerIds.contains(peerId),
                  let chatPeer = transaction.getPeer(peerId),
                  JerkgramBlockedReactionPolicy.isGroupChat(chatPeer) else {
                continue
            }

            let stockUnreadCount = Int(item.readCounters?.count ?? 0)
            let requestedCount = min(512, max(64, stockUnreadCount + 32))
            let historyView = transaction.getMessagesHistoryViewState(
                input: .single(peerId: peerId, threadId: nil),
                ignoreMessagesInTimestampRange: nil,
                ignoreMessageIds: Set(),
                count: requestedCount,
                clipHoles: true,
                anchor: .upperBound,
                namespaces: .just(Set([Namespaces.Message.Cloud]))
            )
            let cacheKey = JerkgramBuild136VisibilityCacheKey(
                accountPeerId: account.peerId,
                peerId: peerId
            )
            if historyView.isLoading {
                removedCacheKeys.insert(cacheKey)
                resolved.removeValue(forKey: peerId)
                continue
            }
            var hiddenUnreadCount: Int32 = 0
            for entry in historyView.entries where !entry.isRead && entry.message.flags.contains(.Incoming) {
                if JerkgramBlockedReactionPolicy.isMessageHidden(
                    accountPeerId: account.peerId,
                    chatPeer: chatPeer,
                    message: entry.message
                ) {
                    hiddenUnreadCount += 1
                }
            }
            let fallbackMessage = historyView.entries.reversed().first(where: { entry in
                !JerkgramBlockedReactionPolicy.isMessageHidden(
                    accountPeerId: account.peerId,
                    chatPeer: chatPeer,
                    message: entry.message
                )
            }).map { EngineMessage($0.message) }
            let cached = JerkgramBuild136VisibilityCacheEntry(
                sourceIndex: item.index,
                stockUnreadCount: stockUnreadCount,
                presentationRevision: presentationRevision,
                fallbackMessage: fallbackMessage,
                hiddenUnreadCount: hiddenUnreadCount
            )
            resolved[peerId] = cached
            if !item.messages.isEmpty || fallbackMessage != nil {
                newCacheEntries[cacheKey] = cached
            } else {
                removedCacheKeys.insert(cacheKey)
                resolved.removeValue(forKey: peerId)
            }
        }
        jerkgramBuild136StoreVisibilityCache(newCacheEntries, removing: removedCacheKeys)
        return buildUpdate(resolved)
    }
}
'''


def patch_chat_list_location(text: str) -> str:
    if CHAT_LIST_MARKER in text:
        require(text.count(CHAT_LIST_MARKER) == 1, "chat-list marker is ambiguous")
        return text
    old_marker = "// MARK: Jerkgram v1.2ZB BUILD135_VISIBLE_CHAT_LIST1"
    start = text.find(old_marker)
    require(start >= 0, "Build135 chat-list helper missing")
    end_anchor = "\npublic func chatListViewForLocation("
    end = text.find(end_anchor, start)
    require(end >= 0, "chat-list helper end anchor missing")
    updated = text[:start] + CHAT_LIST_HELPER + text[end:]
    updated = updated.replace(
        "jerkgramBuild135VisibleChatListUpdate(account: account, update: summarized)",
        "jerkgramBuild136VisibleChatListUpdate(account: account, update: summarized)",
    )
    require(updated.count("jerkgramBuild136VisibleChatListUpdate(account: account, update: summarized)") == 3, "three chat-list flow owners required")
    require("jerkgramBuild135VisibleChatListUpdate" not in updated, "old uncached helper survived")
    return updated


def patch_engine_chat_list(text: str) -> str:
    if ENGINE_ITEM_MARKER in text:
        require(text.count(ENGINE_ITEM_MARKER) == 1, "engine presentation payload marker is ambiguous")
        return text
    text = replace_once(
        text,
        "        public let index: Index\n",
        "        public let index: Index\n        // MARK: Jerkgram v1.2ZC BUILD136_PRESENTATION_PAYLOAD1\n        public let jerkgramPresentationIndex: Index?\n",
        "EngineChatList immutable presentation field",
    )
    text = replace_once(
        text,
        "            mediaDraftContentType: EngineChatList.MediaDraftContentType?\n        ) {",
        "            mediaDraftContentType: EngineChatList.MediaDraftContentType?,\n            jerkgramPresentationIndex: Index? = nil\n        ) {",
        "EngineChatList presentation init parameter",
    )
    text = replace_once(
        text,
        "            self.index = index\n            self.messages = messages\n",
        "            self.index = index\n            self.jerkgramPresentationIndex = jerkgramPresentationIndex\n            self.messages = messages\n",
        "EngineChatList presentation init assignment",
    )
    text = replace_once(
        text,
        "            if lhs.index != rhs.index {\n                return false\n            }\n",
        "            if lhs.index != rhs.index {\n                return false\n            }\n            if lhs.jerkgramPresentationIndex != rhs.jerkgramPresentationIndex {\n                return false\n            }\n",
        "EngineChatList presentation equality",
    )
    text = replace_once(
        text,
        "    func withUpdatedCommunitySummary(messages: [EngineMessage], readCounters: EnginePeerReadCounters?) -> EngineChatList.Item {",
        "    func withUpdatedCommunitySummary(messages: [EngineMessage], readCounters: EnginePeerReadCounters?, jerkgramPresentationIndex: EngineChatList.Item.Index? = nil) -> EngineChatList.Item {",
        "community summary presentation payload",
    )
    text = replace_once(
        text,
        "            mediaDraftContentType: self.mediaDraftContentType\n        )",
        "            mediaDraftContentType: self.mediaDraftContentType,\n            jerkgramPresentationIndex: jerkgramPresentationIndex\n        )",
        "community summary presentation propagation",
    )
    return text


def patch_chat_list_entries(text: str) -> str:
    if ENTRY_MARKER in text:
        require(text.count(ENTRY_MARKER) == 1, "entry marker is ambiguous")
        return text
    peer_start = text.find("    struct PeerEntryData: Equatable {")
    require(peer_start >= 0, "PeerEntryData owner missing")
    peer_end = text.find("\n    struct ContactEntryData: Equatable {", peer_start)
    require(peer_end >= 0, "PeerEntryData end anchor missing")
    peer_block = text[peer_start:peer_end]

    field = "        var index: EngineChatList.Item.Index\n"
    computed = field + r'''        // MARK: Jerkgram v1.2ZC BUILD136_PRESENTATION_SORT_INDEX1
        // This value is supplied only by the group-only visibility processor.
        // `index` remains Telegram's source index for navigation and pagination.
        var jerkgramBuild136PresentationSortIndex: EngineChatList.Item.Index?
'''
    peer_block = replace_once(peer_block, field, computed, "PeerEntry source/presentation index split")

    init_anchor = "            index: EngineChatList.Item.Index,\n            presentationData: ChatListPresentationData,\n"
    if init_anchor in peer_block:
        peer_block = replace_once(
            peer_block,
            init_anchor,
            "            index: EngineChatList.Item.Index,\n            jerkgramBuild136PresentationSortIndex: EngineChatList.Item.Index? = nil,\n            presentationData: ChatListPresentationData,\n",
            "PeerEntry presentation init parameter",
        )
        peer_block = replace_once(
            peer_block,
            "            self.index = index\n            self.presentationData = presentationData\n",
            "            self.index = index\n            self.jerkgramBuild136PresentationSortIndex = jerkgramBuild136PresentationSortIndex\n            self.presentationData = presentationData\n",
            "PeerEntry presentation init assignment",
        )
        peer_block = replace_once(
            peer_block,
            "            if lhs.index != rhs.index {\n                return false\n            }\n",
            "            if lhs.index != rhs.index {\n                return false\n            }\n            if lhs.jerkgramBuild136PresentationSortIndex != rhs.jerkgramBuild136PresentationSortIndex {\n                return false\n            }\n",
            "PeerEntry presentation equality",
        )
    text = text[:peer_start] + peer_block + text[peer_end:]
    text = replace_once(
        text,
        "            return .index(peerEntry.index)\n",
        "            return .index(peerEntry.jerkgramBuild136PresentationSortIndex ?? peerEntry.index)\n",
        "PeerEntry presentation sort owner",
    )
    primary = "        let entry: ChatListNodeEntry = .PeerEntry(ChatListNodeEntry.PeerEntryData(\n            index: offsetPinnedIndex(entry.index, offset: pinnedIndexOffset),\n"
    if primary not in text:
        primary = "    let value = ChatListNodeEntry.PeerEntryData(\n        index: offsetPinnedIndex(entry.index, offset: pinnedIndexOffset),\n"
        replacement = primary + "        jerkgramBuild136PresentationSortIndex: entry.jerkgramPresentationIndex,\n"
    else:
        replacement = primary + "            jerkgramBuild136PresentationSortIndex: entry.jerkgramPresentationIndex,\n"
    text = replace_once(text, primary, replacement, "primary peer entry explicit presentation index")
    return text


def extract_runtime_keys(settings_text: str):
    state_start = settings_text.find("private func jerkgramStateValues(")
    require(state_start >= 0, "account state-map owner missing")
    state_end = settings_text.find("\nprivate func jerkgramPersistChangedSettings(", state_start)
    require(state_end >= 0, "account state-map end anchor missing")
    state_block = settings_text[state_start:state_end]

    enum_values = {
        name: value
        for name, value in re.findall(r'static let (\w+)\s*=\s*"([^"]+)"', settings_text)
    }
    direct_values = {
        name: value
        for name, value in re.findall(r'(?:private\s+)?let (\w+)\s*=\s*"([^"]+)"', settings_text)
    }
    result = []
    seen = set()
    owners = re.findall(r'^\s*(GhostBaseKey\.(\w+)|(\w+))\s*:', state_block, flags=re.MULTILINE)
    for _, enum_name, direct_name in owners:
        value = enum_values.get(enum_name) if enum_name else direct_values.get(direct_name)
        require(value is not None, "unresolved account runtime key: " + (enum_name or direct_name))
        if value.startswith("jerkgram.") and value not in seen:
            seen.add(value)
            result.append(value)
    require("jerkgram.GhostMode.ScheduledSend" in seen, "Scheduled Send runtime key missing")
    return result


def account_helper(runtime_keys):
    literals = "\n".join(f'        "{key}",' for key in runtime_keys)
    return f'''// MARK: Jerkgram v1.2ZC BUILD136_ACCOUNT_PROJECTION1
private func jerkgramBuild135ProjectAccountSettings(accountPeerId: Int64) {{
    let defaults = UserDefaults.standard
    let targetPrefix = "jerkgram.account.\\(accountPeerId).setting."
    let runtimeKeys: [String] = [
{literals}
    ]
    for key in runtimeKeys {{
        let scopedKey = targetPrefix + key
        if let value = defaults.object(forKey: scopedKey) {{
            defaults.set(value, forKey: key)
        }} else {{
            defaults.removeObject(forKey: key)
        }}
    }}

    let scheduledSendKey = "jerkgram.GhostMode.ScheduledSend"
    let sharedDefaults = UserDefaults(suiteName: "group.4a348a9b186b700c.1") ?? defaults
    if let value = defaults.object(forKey: targetPrefix + scheduledSendKey) {{
        sharedDefaults.set(value, forKey: scheduledSendKey)
    }} else {{
        sharedDefaults.removeObject(forKey: scheduledSendKey)
    }}
}}
'''


def patch_account_context(text: str, runtime_keys) -> str:
    if ACCOUNT_MARKER in text:
        require(text.count(ACCOUNT_MARKER) == 1, "account marker is ambiguous")
        return text
    old_marker = "// MARK: Jerkgram v1.2ZB BUILD135_ACCOUNT_RUNTIME1"
    start = text.find(old_marker)
    require(start >= 0, "Build135 account projection helper missing")
    end_anchor = "\npublic final class SharedAccountContext"
    end = text.find(end_anchor, start)
    require(end >= 0, "account projection end anchor missing")
    updated = text[:start] + account_helper(runtime_keys) + text[end:]
    helper = updated[start:updated.find(end_anchor, start)]
    require("dictionaryRepresentation()" not in helper, "full defaults scan survived")
    require("synchronize()" not in helper, "forced defaults synchronization survived")
    return updated


def patch_file(path: Path, transform) -> None:
    require(path.is_file(), "missing source: " + str(path))
    original = path.read_text(encoding="utf-8")
    updated = transform(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")


def main() -> None:
    require(SETTINGS.is_file(), "missing materialized Settings owner")
    runtime_keys = extract_runtime_keys(SETTINGS.read_text(encoding="utf-8"))
    patch_file(REACTION_POLICY, patch_policy)
    patch_file(ENGINE_CHAT_LIST, patch_engine_chat_list)
    patch_file(CHAT_LIST_LOCATION, patch_chat_list_location)
    patch_file(CHAT_LIST_ENTRIES, patch_chat_list_entries)
    patch_file(SHARED_ACCOUNT_CONTEXT, lambda text: patch_account_context(text, runtime_keys))
    print("[Build136 visible order/cache] SOURCE PATCHED")
    print("[Build136 visible order/cache] source navigation index + visible row index + signature cache + bounded account projection")


if __name__ == "__main__":
    main()
