#!/usr/bin/env python3

from pathlib import Path
import os
import re


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()

BLOCKED_CONTEXT = ROOT / "submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeersContext.swift"
STORE_MESSAGE = ROOT / "submodules/TelegramCore/Sources/ApiUtils/StoreMessage_Telegram.swift"
ACCOUNT_VIEW_TRACKER = ROOT / "submodules/TelegramCore/Sources/State/AccountViewTracker.swift"
DELETE_MESSAGES = ROOT / "submodules/TelegramCore/Sources/TelegramEngine/Messages/DeleteMessages.swift"
CHAT_LIST = ROOT / "submodules/TelegramCore/Sources/TelegramEngine/Messages/ChatList.swift"
NAVIGATION = ROOT / "submodules/TelegramCore/Sources/TelegramEngine/Messages/EarliestUnseenPersonalMentionMessage.swift"
CHAT_HISTORY_ENTRIES = ROOT / "submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift"
CHAT_HISTORY_LIST = ROOT / "submodules/TelegramUI/Sources/ChatHistoryListNode.swift"

POLICY_MARKER = "// MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_POLICY1"
STORE_MARKER = "// MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_STORE1"
TRACKER_MARKER = "// MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_TRACKER1"
DELETE_MARKER = "// MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_DELETE1"
CHAT_LIST_MARKER = "// MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_CHAT_LIST1"
NAV_MARKER = "// MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_NAVIGATION1"
HISTORY_ENTRIES_MARKER = "// MARK: Jerkgram v1.2U BUILD133_BLOCKED_MESSAGE_HISTORY2"
HISTORY_REFRESH_MARKER = "// MARK: Jerkgram v1.2U BUILD133_BLOCKED_VISIBILITY_REFRESH2"
V12T_POLICY_MARKER = "// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_POLICY1"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 blocked activity] " + message)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    require(count == 1, f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def visible_navigation_target(targets, blocked, enabled=True):
    for target_id, actor, exists in targets:
        if not exists:
            continue
        if enabled and actor is not None and actor in blocked:
            continue
        return target_id
    return None


def visible_activity(*, stock, summary_count, loaded, blocked, enabled=True):
    if not stock:
        return False
    if not enabled:
        return stock
    existing = [(actor, exists) for actor, exists in loaded if exists]
    if summary_count <= 0:
        return False
    for actor, _ in existing:
        if actor is None or actor not in blocked:
            return stock
    return False


def visible_chat_messages(messages, blocked, *, account, enabled=True):
    if not enabled:
        return list(messages)
    return [item for item in messages if item[1] == account or item[1] not in blocked]


POLICY_EXTENSION = r'''
    // MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_POLICY1
    public static func hideBlockedMessages(accountPeerId: PeerId) -> Bool {
        let defaults = UserDefaults.standard
        let scopedKey = "jerkgram.account.\(accountPeerId.toInt64()).setting.\(self.hideBlockedMessagesKey)"
        if let value = defaults.object(forKey: scopedKey) as? Bool {
            return value
        }
        if let value = defaults.object(forKey: self.hideBlockedMessagesKey) as? Bool {
            return value
        }
        return true
    }

    public static func isMessageHidden(accountPeerId: PeerId, authorId: PeerId?) -> Bool {
        guard self.hideBlockedMessages(accountPeerId: accountPeerId) else {
            return false
        }
        guard let authorId, authorId != accountPeerId else {
            return false
        }
        return self.isBlocked(accountPeerId: accountPeerId, peerId: authorId)
    }

    public static func hasVisibleUnseenReaction(
        accountPeerId: PeerId,
        attribute: ReactionsMessageAttribute
    ) -> Bool {
        guard attribute.hasUnseen else {
            return false
        }
        guard self.hideBlockedReactions(accountPeerId: accountPeerId) else {
            return true
        }

        var sawUnseen = false
        for recentPeer in attribute.recentPeers where recentPeer.isUnseen {
            sawUnseen = true
            if recentPeer.isMy || recentPeer.peerId == accountPeerId {
                return true
            }
            if !self.isBlocked(accountPeerId: accountPeerId, peerId: recentPeer.peerId) {
                return true
            }
        }

        if !sawUnseen {
            return true
        }
        return false
    }
'''


STORE_HELPER = r'''

// MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_STORE1
private func jerkgramBuild133FilteredActivityTags(
    accountPeerId: PeerId,
    authorId: PeerId?,
    attributes: [MessageAttribute],
    tags: MessageTags
) -> MessageTags {
    var tags = tags

    if tags.contains(.unseenPersonalMessage),
       JerkgramBlockedReactionPolicy.isMessageHidden(
            accountPeerId: accountPeerId,
            authorId: authorId
       ) {
        tags.remove(.unseenPersonalMessage)
    }

    if tags.contains(.unseenReaction),
       let attribute = attributes.first(where: { $0 is ReactionsMessageAttribute }) as? ReactionsMessageAttribute,
       !JerkgramBlockedReactionPolicy.hasVisibleUnseenReaction(
            accountPeerId: accountPeerId,
            attribute: attribute
       ) {
        tags.remove(.unseenReaction)
    }

    return tags
}
'''


CHAT_LIST_HELPER = r'''

// MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_CHAT_LIST1
private func jerkgramBuild133ActivityVisible(
    stock: Bool,
    expectedCount: Int,
    accountPeerId: PeerId?,
    messages: [Message],
    tag: MessageTags,
    hidden: (PeerId, Message) -> Bool
) -> Bool {
    guard stock else {
        return false
    }
    guard expectedCount > 0, let accountPeerId else {
        return stock
    }

    let taggedMessages = messages.filter { $0.tags.contains(tag) }
    for message in taggedMessages {
        if !hidden(accountPeerId, message) {
            return true
        }
    }
    // A stale summary may count an entry already removed by blocked-message
    // filtering. If every materialized target is hidden, do not expose a dead
    // chat-list badge or navigation button.
    return false
}

private func jerkgramBuild133ReactionActivityHidden(
    accountPeerId: PeerId,
    message: Message
) -> Bool {
    if JerkgramBlockedReactionPolicy.isMessageHidden(
        accountPeerId: accountPeerId,
        authorId: message.author?.id
    ) {
        return true
    }
    guard let attribute = message.attributes.first(where: { $0 is ReactionsMessageAttribute }) as? ReactionsMessageAttribute else {
        return false
    }
    return !JerkgramBlockedReactionPolicy.hasVisibleUnseenReaction(
        accountPeerId: accountPeerId,
        attribute: attribute
    )
}
'''


NAV_HELPER = r'''

// MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_NAVIGATION1
private enum JerkgramBuild133UnseenTargetKind {
    case mention
    case reaction
}

private func jerkgramBuild133IsNavigableUnseenTarget(
    accountPeerId: PeerId,
    message: Message,
    kind: JerkgramBuild133UnseenTargetKind
) -> Bool {
    if JerkgramBlockedReactionPolicy.isMessageHidden(
        accountPeerId: accountPeerId,
        authorId: message.author?.id
    ) {
        return false
    }

    switch kind {
    case .mention:
        return true
    case .reaction:
        guard let attribute = message.attributes.first(where: { $0 is ReactionsMessageAttribute }) as? ReactionsMessageAttribute else {
            return true
        }
        return JerkgramBlockedReactionPolicy.hasVisibleUnseenReaction(
            accountPeerId: accountPeerId,
            attribute: attribute
        )
    }
}

private func jerkgramBuild133FirstNavigableUnseenTarget(
    accountPeerId: PeerId,
    entries: [MessageHistoryEntry],
    kind: JerkgramBuild133UnseenTargetKind
) -> Message? {
    for entry in entries {
        if jerkgramBuild133IsNavigableUnseenTarget(
            accountPeerId: accountPeerId,
            message: entry.message,
            kind: kind
        ) {
            return entry.message
        }
    }
    return nil
}
'''


def patch_policy(text: str) -> str:
    require(V12T_POLICY_MARKER in text, "v12t blocked reaction policy prerequisite missing")
    if POLICY_MARKER in text:
        require(text.count(POLICY_MARKER) == 1, "activity policy marker is ambiguous")
        return text
    anchor = r'''    public static func hideBlockedReactions(accountPeerId: PeerId) -> Bool {
        let defaults = UserDefaults.standard
        let scopedKey = "jerkgram.account.\(accountPeerId.toInt64()).setting.\(self.hideBlockedReactionsKey)"
        if let value = defaults.object(forKey: scopedKey) as? Bool {
            return value
        }
        if let value = defaults.object(forKey: self.hideBlockedReactionsKey) as? Bool {
            return value
        }
        return true
    }
'''
    require(text.count(anchor) == 1, "v12t hideBlockedReactions owner is missing or ambiguous")
    return text.replace(anchor, anchor + POLICY_EXTENSION, 1)


def patch_store_message(text: str) -> str:
    if STORE_MARKER in text:
        require(text.count(STORE_MARKER) == 1, "StoreMessage marker is ambiguous")
        return text

    insert_anchor = "\nfunc apiMessagePeerId(_ messsage: Api.Message) -> PeerId? {"
    require(text.count(insert_anchor) == 1, "StoreMessage helper insertion anchor mismatch")
    text = text.replace(insert_anchor, STORE_HELPER + insert_anchor, 1)

    pattern = re.compile(
        r'(?m)^(?P<indent>[ \t]*)let \(tags, globalTags\) = '
        r'tagsForStoreMessage\((?P<args>[^\n]+)\)$'
    )
    matches = list(pattern.finditer(text))
    require(len(matches) == 2, f"StoreMessage tag call sites: expected 2, found {len(matches)}")

    def repl(match):
        indent = match.group("indent")
        args = match.group("args")
        return (
            f"{indent}let (jerkgramBuild133RawTags, globalTags) = tagsForStoreMessage({args})\n"
            f"{indent}let tags = jerkgramBuild133FilteredActivityTags(\n"
            f"{indent}    accountPeerId: accountPeerId,\n"
            f"{indent}    authorId: authorId,\n"
            f"{indent}    attributes: attributes,\n"
            f"{indent}    tags: jerkgramBuild133RawTags\n"
            f"{indent})"
        )

    text = pattern.sub(repl, text)
    require(text.count("jerkgramBuild133FilteredActivityTags(") == 3, "StoreMessage helper/call count mismatch")
    return text


def patch_account_view_tracker(text: str) -> str:
    if TRACKER_MARKER in text:
        require(text.count(TRACKER_MARKER) == 1, "AccountViewTracker marker is ambiguous")
        return text
    old = '''                                                    var tags = currentMessage.tags
                                                    if updatedReactions.hasUnseen {
                                                        tags.insert(.unseenReaction)
                                                    } else {
                                                        tags.remove(.unseenReaction)
                                                    }'''
    new = '''                                                    // MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_TRACKER1
                                                    var tags = currentMessage.tags
                                                    if JerkgramBlockedReactionPolicy.hasVisibleUnseenReaction(
                                                        accountPeerId: account.peerId,
                                                        attribute: updatedReactions
                                                    ) {
                                                        tags.insert(.unseenReaction)
                                                    } else {
                                                        tags.remove(.unseenReaction)
                                                    }'''
    return replace_once(text, old, new, "AccountViewTracker unseen reaction tag owner")


def patch_delete_messages(text: str) -> str:
    if DELETE_MARKER in text:
        require(text.count(DELETE_MARKER) == 2, "DeleteMessages marker count mismatch")
        return text
    old = '''                var tags = currentMessage.tags
                if attributes.contains(where: { ($0 as? ReactionsMessageAttribute)?.hasUnseen == true }) {
                    tags.insert(.unseenReaction)
                } else {
                    tags.remove(.unseenReaction)
                }'''
    require(text.count(old) == 2, f"DeleteMessages unseen reaction owners: expected 2, found {text.count(old)}")
    new = '''                // MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_DELETE1
                var tags = currentMessage.tags
                let hasVisibleUnseenReaction = attributes.compactMap { $0 as? ReactionsMessageAttribute }.contains(where: {
                    JerkgramBlockedReactionPolicy.hasVisibleUnseenReaction(
                        accountPeerId: account.peerId,
                        attribute: $0
                    )
                })
                if hasVisibleUnseenReaction {
                    tags.insert(.unseenReaction)
                } else {
                    tags.remove(.unseenReaction)
                }'''
    return text.replace(old, new)


def patch_chat_list(text: str) -> str:
    if CHAT_LIST_MARKER in text:
        require(text.count(CHAT_LIST_MARKER) == 1, "ChatList marker is ambiguous")
        return text

    owner_anchor = "\nextension EngineChatList.Item {"
    require(text.count(owner_anchor) >= 1, "EngineChatList.Item extension owner missing")
    text = text.replace(owner_anchor, CHAT_LIST_HELPER + owner_anchor, 1)

    mention_old = '''            var hasUnseenMentions = false
            if let info = tagSummaryInfo[ChatListEntryMessageTagSummaryKey(
                tag: .unseenPersonalMessage,
                actionType: PendingMessageActionType.consumeUnseenPersonalMessage
            )] {
                hasUnseenMentions = (info.tagSummaryCount ?? 0) > (info.actionsSummaryCount ?? 0)
            }'''
    mention_new = '''            var hasUnseenMentions = false
            if let info = tagSummaryInfo[ChatListEntryMessageTagSummaryKey(
                tag: .unseenPersonalMessage,
                actionType: PendingMessageActionType.consumeUnseenPersonalMessage
            )] {
                let tagCount = Int(info.tagSummaryCount ?? 0)
                let actionCount = Int(info.actionsSummaryCount ?? 0)
                let outstandingCount = max(0, tagCount - actionCount)
                let stockHasUnseenMentions = outstandingCount > 0
                hasUnseenMentions = jerkgramBuild133ActivityVisible(
                    stock: stockHasUnseenMentions,
                    expectedCount: outstandingCount,
                    accountPeerId: accountPeerId,
                    messages: messages,
                    tag: .unseenPersonalMessage,
                    hidden: { accountPeerId, message in
                        JerkgramBlockedReactionPolicy.isMessageHidden(
                            accountPeerId: accountPeerId,
                            authorId: message.author?.id
                        )
                    }
                )
            }'''
    text = replace_once(text, mention_old, mention_new, "ChatList mention summary owner")

    reaction_old = '''            var hasUnseenReactions = false
            if let info = tagSummaryInfo[ChatListEntryMessageTagSummaryKey(
                tag: .unseenReaction,
                actionType: PendingMessageActionType.readReactionOrPollVote
            )] {
                hasUnseenReactions = (info.tagSummaryCount ?? 0) != 0
            }'''
    reaction_new = '''            var hasUnseenReactions = false
            if let info = tagSummaryInfo[ChatListEntryMessageTagSummaryKey(
                tag: .unseenReaction,
                actionType: PendingMessageActionType.readReactionOrPollVote
            )] {
                let outstandingCount = Int(info.tagSummaryCount ?? 0)
                let stockHasUnseenReactions = outstandingCount != 0
                hasUnseenReactions = jerkgramBuild133ActivityVisible(
                    stock: stockHasUnseenReactions,
                    expectedCount: outstandingCount,
                    accountPeerId: accountPeerId,
                    messages: messages,
                    tag: .unseenReaction,
                    hidden: jerkgramBuild133ReactionActivityHidden
                )
            }'''
    return replace_once(text, reaction_old, reaction_new, "ChatList reaction summary owner")


def _replace_navigation_function(text: str, function_name: str, kind: str) -> str:
    signature = f"func {function_name}("
    start = text.find(signature)
    require(start >= 0, f"navigation owner missing: {function_name}")
    next_func = text.find("\nfunc ", start + len(signature))
    end = len(text) if next_func < 0 else next_func
    block = text[start:end]

    count_old = "count: 4, fixedCombinedReadStates:"
    require(block.count(count_old) == 1, f"{function_name}: history count anchor mismatch")
    block = block.replace(count_old, "count: 64, fixedCombinedReadStates:", 1)

    old = "        if let message = view.0.entries.first?.message {\n"
    require(block.count(old) == 1, f"{function_name}: first target anchor mismatch")
    new = (
        "        if let message = jerkgramBuild133FirstNavigableUnseenTarget(\n"
        "            accountPeerId: account.peerId,\n"
        "            entries: view.0.entries,\n"
        f"            kind: .{kind}\n"
        "        ) {\n"
    )
    block = block.replace(old, new, 1)

    cleanup_anchor = "        } else {\n            return account.postbox.transaction"
    require(block.count(cleanup_anchor) == 1, f"{function_name}: empty-history cleanup anchor mismatch")
    cleanup_new = (
        "        } else if !view.0.entries.isEmpty {\n"
        "            return .single(.result(nil))\n"
        "        } else {\n"
        "            return account.postbox.transaction"
    )
    block = block.replace(cleanup_anchor, cleanup_new, 1)
    return text[:start] + block + text[end:]


def patch_navigation(text: str) -> str:
    if NAV_MARKER in text:
        require(text.count(NAV_MARKER) == 1, "navigation marker is ambiguous")
        return text

    insert_anchor = "\nfunc _internal_earliestUnseenPersonalMentionMessage("
    require(text.count(insert_anchor) == 1, "navigation helper insertion anchor mismatch")
    text = text.replace(insert_anchor, NAV_HELPER + insert_anchor, 1)

    text = _replace_navigation_function(text, "_internal_earliestUnseenPersonalMentionMessage", "mention")
    text = _replace_navigation_function(text, "_internal_earliestUnseenPersonalReactionMessage", "reaction")
    require("_internal_earliestUnseenPollVoteMessage" in text, "poll-vote navigation owner disappeared")
    return text


def patch_chat_history_entries(text: str) -> str:
    if HISTORY_ENTRIES_MARKER in text:
        require(text.count(HISTORY_ENTRIES_MARKER) == 1, "chat history message marker is ambiguous")
        return text

    anchor = '''        if pendingRemovedMessages.contains(message.id) {
            continue
        }
'''
    replacement = anchor + '''
        // MARK: Jerkgram v1.2U BUILD133_BLOCKED_MESSAGE_HISTORY2
        // Presentation-only filtering: Postbox contents stay untouched, so
        // switching the option off restores the messages immediately.
        if JerkgramBlockedReactionPolicy.isMessageHidden(
            accountPeerId: context.account.peerId,
            authorId: message.author?.id
        ) {
            continue loop
        }
'''
    return replace_once(text, anchor, replacement, "chat history blocked-message presentation gate")


def patch_chat_history_list(text: str) -> str:
    if HISTORY_REFRESH_MARKER in text:
        require(text.count(HISTORY_REFRESH_MARKER) == 1, "chat history refresh marker is ambiguous")
        return text

    anchor = "        let historyViewUpdateValue = historyViewUpdate\n"
    replacement = '''        // MARK: Jerkgram v1.2U BUILD133_BLOCKED_VISIBILITY_REFRESH2
        // Rebuild visible entries when either the Telegram blocked list or a
        // Jerkgram visibility switch changes; no chat reload/restart required.
        let historyViewUpdateValue = combineLatest(
            historyViewUpdate,
            JerkgramBlockedReactionPolicy.presentationUpdates
        )
        |> map { update, _ in
            return update
        }
'''
    return replace_once(text, anchor, replacement, "chat history live visibility refresh")


def main() -> None:
    owners = (BLOCKED_CONTEXT, STORE_MESSAGE, ACCOUNT_VIEW_TRACKER, DELETE_MESSAGES, CHAT_LIST, NAVIGATION, CHAT_HISTORY_ENTRIES, CHAT_HISTORY_LIST)
    for path in owners:
        require(path.is_file(), "missing source owner: " + str(path))

    patched = {
        BLOCKED_CONTEXT: patch_policy(BLOCKED_CONTEXT.read_text(encoding="utf-8")),
        STORE_MESSAGE: patch_store_message(STORE_MESSAGE.read_text(encoding="utf-8")),
        ACCOUNT_VIEW_TRACKER: patch_account_view_tracker(ACCOUNT_VIEW_TRACKER.read_text(encoding="utf-8")),
        DELETE_MESSAGES: patch_delete_messages(DELETE_MESSAGES.read_text(encoding="utf-8")),
        CHAT_LIST: patch_chat_list(CHAT_LIST.read_text(encoding="utf-8")),
        NAVIGATION: patch_navigation(NAVIGATION.read_text(encoding="utf-8")),
        CHAT_HISTORY_ENTRIES: patch_chat_history_entries(CHAT_HISTORY_ENTRIES.read_text(encoding="utf-8")),
        CHAT_HISTORY_LIST: patch_chat_history_list(CHAT_HISTORY_LIST.read_text(encoding="utf-8")),
    }

    for path, text in patched.items():
        path.write_text(text, encoding="utf-8")

    print("[Build133 blocked activity] SOURCE PATCHED")


if __name__ == "__main__":
    main()
