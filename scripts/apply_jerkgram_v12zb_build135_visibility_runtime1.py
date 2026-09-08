#!/usr/bin/env python3

from pathlib import Path
import os


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
CHAT_LIST_LOCATION = ROOT / "submodules/ChatListUI/Sources/Node/ChatListNodeLocation.swift"
CHAT_UNREAD = ROOT / "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift"
SHARED_ACCOUNT_CONTEXT = ROOT / "submodules/TelegramUI/Sources/SharedAccountContext.swift"

CHAT_LIST_MARKER = "// MARK: Jerkgram v1.2ZB BUILD135_VISIBLE_CHAT_LIST1"
CHAT_UNREAD_MARKER = "// MARK: Jerkgram v1.2ZB BUILD135_VISIBLE_UNREAD1"
ACCOUNT_MARKER = "// MARK: Jerkgram v1.2ZB BUILD135_ACCOUNT_RUNTIME1"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build135 visibility/runtime] " + message)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    require(count == 1, f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def visible_preview(messages, blocked, *, account, enabled=True, chat_kind="group"):
    if chat_kind not in ("group", "supergroup") or not enabled:
        return messages[0] if messages else None
    return next((item for item in messages if item[1] == account or item[1] not in blocked), None)


def visible_unread_count(stock_count, entries, blocked, *, account, enabled=True, chat_kind="group"):
    if chat_kind not in ("group", "supergroup") or not enabled:
        return stock_count
    hidden_unread = sum(1 for author, is_read in entries if not is_read and author != account and author in blocked)
    return max(0, stock_count - hidden_unread)


def project_account_settings(defaults, *, account_peer_id):
    result = dict(defaults)
    marker = ".setting."
    suffixes = {
        key.split(marker, 1)[1]
        for key in result
        if key.startswith("jerkgram.account.") and marker in key
    }
    prefix = f"jerkgram.account.{account_peer_id}.setting."
    for suffix in suffixes:
        scoped = prefix + suffix
        if scoped in result:
            result[suffix] = result[scoped]
        else:
            result.pop(suffix, None)
    return result


CHAT_LIST_HELPER = r'''

// MARK: Jerkgram v1.2ZB BUILD135_VISIBLE_CHAT_LIST1
private func jerkgramBuild135ReadCounters(
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

private func jerkgramBuild135VisibleChatListUpdate(
    account: Account,
    update: ChatListNodeViewUpdate
) -> Signal<ChatListNodeViewUpdate, NoError> {
    let needsInspection = update.list.items.contains { item in
        guard let peer = item.renderedPeer.peer else {
            return false
        }
        return JerkgramBlockedReactionPolicy.isGroupChat(peer._asPeer())
            && (item.messages.isEmpty || (item.readCounters?.count ?? 0) > 0)
    }
    guard needsInspection, JerkgramBlockedReactionPolicy.hideBlockedMessages(accountPeerId: account.peerId) else {
        return .single(update)
    }

    return account.postbox.transaction { transaction -> ChatListNodeViewUpdate in
        let items = update.list.items.map { item -> EngineChatList.Item in
            guard case let .chatList(peerId) = item.id,
                  let chatPeer = transaction.getPeer(peerId),
                  JerkgramBlockedReactionPolicy.isGroupChat(chatPeer),
                  item.messages.isEmpty || (item.readCounters?.count ?? 0) > 0 else {
                return item
            }

            let requestedCount = min(512, max(64, Int(item.readCounters?.count ?? 0) + 32))
            let historyView = transaction.getMessagesHistoryViewState(
                input: .single(peerId: peerId, threadId: nil),
                ignoreMessagesInTimestampRange: nil,
                ignoreMessageIds: Set(),
                count: requestedCount,
                clipHoles: true,
                anchor: .upperBound,
                namespaces: .just(Set([Namespaces.Message.Cloud]))
            )
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

            var messages = item.messages
            if messages.isEmpty, let fallback = historyView.entries.reversed().first(where: { entry in
                !JerkgramBlockedReactionPolicy.isMessageHidden(
                    accountPeerId: account.peerId,
                    chatPeer: chatPeer,
                    message: entry.message
                )
            }) {
                messages = [EngineMessage(fallback.message)]
            }
            return item.withUpdatedCommunitySummary(
                messages: messages,
                readCounters: jerkgramBuild135ReadCounters(item.readCounters, subtracting: hiddenUnreadCount)
            )
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
}
'''


CHAT_UNREAD_HELPER = r'''

// MARK: Jerkgram v1.2ZB BUILD135_VISIBLE_UNREAD1
private func jerkgramBuild135VisibleUnreadCount(
    account: Account,
    peerId: PeerId?,
    stockCount: Int
) -> Signal<Int, NoError> {
    guard stockCount > 0, let peerId else {
        return .single(stockCount)
    }
    return account.postbox.transaction { transaction -> Int in
        guard let chatPeer = transaction.getPeer(peerId),
              JerkgramBlockedReactionPolicy.isGroupChat(chatPeer),
              JerkgramBlockedReactionPolicy.hideBlockedMessages(accountPeerId: account.peerId) else {
            return stockCount
        }
        let requestedCount = min(512, max(64, stockCount + 32))
        let historyView = transaction.getMessagesHistoryViewState(
            input: .single(peerId: peerId, threadId: nil),
            ignoreMessagesInTimestampRange: nil,
            ignoreMessageIds: Set(),
            count: requestedCount,
            clipHoles: true,
            anchor: .upperBound,
            namespaces: .just(Set([Namespaces.Message.Cloud]))
        )
        var hiddenUnreadCount = 0
        for entry in historyView.entries where !entry.isRead && entry.message.flags.contains(.Incoming) {
            if JerkgramBlockedReactionPolicy.isMessageHidden(
                accountPeerId: account.peerId,
                chatPeer: chatPeer,
                message: entry.message
            ) {
                hiddenUnreadCount += 1
            }
        }
        return max(0, stockCount - hiddenUnreadCount)
    }
}
'''


ACCOUNT_HELPER = r'''

// MARK: Jerkgram v1.2ZB BUILD135_ACCOUNT_RUNTIME1
private func jerkgramBuild135ProjectAccountSettings(accountPeerId: Int64) {
    let defaults = UserDefaults.standard
    let marker = ".setting."
    let targetPrefix = "jerkgram.account.\(accountPeerId).setting."
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

    let scheduledSendKey = "jerkgram.GhostMode.ScheduledSend"
    let sharedDefaults = UserDefaults(suiteName: "group.4a348a9b186b700c.1") ?? defaults
    if let value = defaults.object(forKey: targetPrefix + scheduledSendKey) {
        sharedDefaults.set(value, forKey: scheduledSendKey)
    } else {
        sharedDefaults.removeObject(forKey: scheduledSendKey)
    }
    defaults.synchronize()
    sharedDefaults.synchronize()
}
'''


def patch_chat_list_location(text: str) -> str:
    if CHAT_LIST_MARKER in text:
        require(text.count(CHAT_LIST_MARKER) == 1, "chat-list marker is ambiguous")
        return text
    text = replace_once(text, "\npublic func chatListViewForLocation(", CHAT_LIST_HELPER + "\npublic func chatListViewForLocation(", "chat-list helper")
    owner = "                return chatListNodeViewUpdateWithCommunitySummaries(account: account, update: update)"
    replacement = owner + "\n                |> mapToSignal { summarized in\n                    return jerkgramBuild135VisibleChatListUpdate(account: account, update: summarized)\n                }"
    count = text.count(owner)
    if count:
        require(count == 3, f"chat-list flow owners: expected three, found {count}")
        text = text.replace(owner, replacement)
    return text


def patch_chat_unread(text: str) -> str:
    if CHAT_UNREAD_MARKER in text:
        require(text.count(CHAT_UNREAD_MARKER) == 1, "chat unread marker is ambiguous")
        return text
    text = replace_once(text, "\n    func setupChatHistoryNode(historyNode: ChatHistoryListNodeImpl) {", CHAT_UNREAD_HELPER + "\n    func setupChatHistoryNode(historyNode: ChatHistoryListNodeImpl) {", "chat unread helper")
    old = "                let throttledUnreadCountSignal = self.context.chatLocationUnreadCount(for: self.chatLocation, contextHolder: self.chatLocationContextHolder)\n                |> mapToThrottled { value -> Signal<Int, NoError> in"
    new = "                let throttledUnreadCountSignal = combineLatest(\n                    self.context.chatLocationUnreadCount(for: self.chatLocation, contextHolder: self.chatLocationContextHolder),\n                    JerkgramBlockedReactionPolicy.presentationUpdates\n                )\n                |> mapToSignal { [weak self] count, _ -> Signal<Int, NoError> in\n                    guard let self else {\n                        return .single(count)\n                    }\n                    return jerkgramBuild135VisibleUnreadCount(\n                        account: self.context.account,\n                        peerId: self.chatLocation.peerId,\n                        stockCount: count\n                    )\n                }\n                |> mapToThrottled { value -> Signal<Int, NoError> in"
    if old in text:
        text = replace_once(text, old, new, "chat unread signal")
    return text


def patch_shared_account_context(text: str) -> str:
    if ACCOUNT_MARKER in text:
        require(text.count(ACCOUNT_MARKER) == 1, "account marker is ambiguous")
        return text
    text = replace_once(text, "\npublic final class SharedAccountContext", ACCOUNT_HELPER + "\npublic final class SharedAccountContext", "account helper")

    switching = "        self.switchingData = (settingsController as? (ViewController & SettingsController), chatListController as? ChatListController, chatsBadge)\n        \n        let _ = self.accountManager.transaction"
    projection = "        self.switchingData = (settingsController as? (ViewController & SettingsController), chatListController as? ChatListController, chatsBadge)\n        if let target = self.activeAccountsValue?.accounts.first(where: { $0.0 == id })?.1 {\n            jerkgramBuild135ProjectAccountSettings(accountPeerId: target.account.peerId.toInt64())\n        }\n        \n        let _ = self.accountManager.transaction"
    if switching in text:
        text = replace_once(text, switching, projection, "account switch projection")
    else:
        test_anchor = "        let _ = self.accountManager.transaction({ transaction -> Bool in"
        text = replace_once(text, test_anchor, "        if let target = self.activeAccountsValue?.accounts.first(where: { $0.0 == id })?.1 {\n            jerkgramBuild135ProjectAccountSettings(accountPeerId: target.account.peerId.toInt64())\n        }\n        " + test_anchor.lstrip(), "fixture account switch projection")

    primary = "                    self.activeAccountsValue!.primary = primary"
    if primary in text:
        text = replace_once(text, primary, primary + "\n                    if let primary {\n                        jerkgramBuild135ProjectAccountSettings(accountPeerId: primary.account.peerId.toInt64())\n                    }", "primary account projection")
    return text


def patch_file(path: Path, transform) -> None:
    require(path.is_file(), "missing source: " + str(path))
    original = path.read_text(encoding="utf-8")
    updated = transform(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")


def main() -> None:
    patch_file(CHAT_LIST_LOCATION, patch_chat_list_location)
    patch_file(CHAT_UNREAD, patch_chat_unread)
    patch_file(SHARED_ACCOUNT_CONTEXT, patch_shared_account_context)
    print("[Build135 visibility/runtime] SOURCE PATCHED")
    print("[Build135 visibility/runtime] previous visible preview + filtered unread badges + synchronous per-account runtime")


if __name__ == "__main__":
    main()
