#!/usr/bin/env python3

from pathlib import Path
import os


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


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 blocked activity verifier] " + message)


def function_block(text: str, name: str) -> str:
    signature = f"func {name}("
    start = text.find(signature)
    require(start >= 0, "missing function: " + name)
    next_func = text.find("\nfunc ", start + len(signature))
    if next_func < 0:
        return text[start:]
    return text[start:next_func]


def verify_chat_list_owner(text: str) -> None:
    require(text.count(CHAT_LIST_MARKER) == 1, "ChatList marker count")
    require("private func jerkgramBuild133ActivityVisible(" in text, "ChatList evidence helper missing")
    require("private func jerkgramBuild133ReactionActivityHidden(" in text, "reaction activity helper missing")
    require("expectedCount: outstandingCount" in text, "bounded evidence count missing")
    require("tag: .unseenPersonalMessage" in text, "mention activity tag missing")
    require("tag: .unseenReaction" in text, "reaction activity tag missing")
    require(
        "JerkgramBlockedReactionPolicy.isMessageHidden(" in text,
        "blocked-message policy is not used by chat-list owner",
    )
    require(
        "JerkgramBlockedReactionPolicy.hasVisibleUnseenReaction(" in text,
        "blocked-reaction policy is not used by chat-list owner",
    )
    require(
        "hasUnseenMentions = (info.tagSummaryCount ?? 0) > (info.actionsSummaryCount ?? 0)" not in text,
        "stock mention assignment survived active owner",
    )
    require(
        "hasUnseenReactions = (info.tagSummaryCount ?? 0) != 0" not in text,
        "stock reaction assignment survived active owner",
    )


def verify_navigation_owner(text: str) -> None:
    require(text.count(NAV_MARKER) == 1, "navigation marker count")
    require("private func jerkgramBuild133FirstNavigableUnseenTarget(" in text, "target filter helper missing")
    require("private func jerkgramBuild133IsNavigableUnseenTarget(" in text, "target visibility helper missing")

    mention = function_block(text, "_internal_earliestUnseenPersonalMentionMessage")
    reaction = function_block(text, "_internal_earliestUnseenPersonalReactionMessage")
    poll = function_block(text, "_internal_earliestUnseenPollVoteMessage")

    for label, block, kind in (
        ("mention", mention, ".mention"),
        ("reaction", reaction, ".reaction"),
    ):
        require("jerkgramBuild133FirstNavigableUnseenTarget(" in block, label + " does not filter target before result")
        require(kind in block, label + " target kind missing")
        require("entries: view.0.entries" in block, label + " entries are not filtered")
        require("else if !view.0.entries.isEmpty" in block, label + " filtered-empty guard missing")
        require("count: 64, fixedCombinedReadStates:" in block, label + " bounded target window missing")
        require("view.0.entries.first?.message" not in block, label + " stock first-target path survived")

    require("jerkgramBuild133FirstNavigableUnseenTarget(" not in poll, "poll-vote navigation was modified")
    require("count: 4, fixedCombinedReadStates:" in poll, "poll-vote stock history window changed")


def verify_policy(text: str) -> None:
    require(text.count(POLICY_MARKER) == 1, "policy marker count")
    require("public static func hideBlockedMessages(" in text, "hideBlockedMessages policy missing")
    require("public static func isMessageHidden(" in text, "message visibility policy missing")
    require("public static func hasVisibleUnseenReaction(" in text, "unseen reaction policy missing")
    require("if !sawUnseen {" in text and "return true" in text, "unknown reaction evidence fallback missing")
    require("blockedPeerIdsByAccount" in text, "shared v12t blocked cache missing")


def verify_store_owner(text: str) -> None:
    require(text.count(STORE_MARKER) == 1, "StoreMessage marker count")
    require(text.count("jerkgramBuild133FilteredActivityTags(") == 3, "StoreMessage helper/call count")
    require("tags.remove(.unseenPersonalMessage)" in text, "mention tag suppression missing")
    require("tags.remove(.unseenReaction)" in text, "reaction tag suppression missing")
    require(text.count("let (jerkgramBuild133RawTags, globalTags) = tagsForStoreMessage(") == 2, "StoreMessage call sites not both patched")


def verify_refresh_owners(tracker: str, delete_messages: str) -> None:
    require(tracker.count(TRACKER_MARKER) == 1, "AccountViewTracker marker count")
    require(
        "if JerkgramBlockedReactionPolicy.hasVisibleUnseenReaction(" in tracker,
        "AccountViewTracker still uses raw hasUnseen",
    )
    require("if updatedReactions.hasUnseen {" not in tracker, "AccountViewTracker raw unseen owner survived")

    require(delete_messages.count(DELETE_MARKER) == 2, "DeleteMessages two-owner marker count")
    require(
        delete_messages.count("JerkgramBlockedReactionPolicy.hasVisibleUnseenReaction(") == 2,
        "DeleteMessages two reaction refresh owners not patched",
    )
    require(
        "attributes.contains(where: { ($0 as? ReactionsMessageAttribute)?.hasUnseen == true })" not in delete_messages,
        "DeleteMessages raw unseen owner survived",
    )


def verify_chat_history_owners(entries: str, history_list: str) -> None:
    require(entries.count(HISTORY_ENTRIES_MARKER) == 1, "chat history message-filter marker count")
    require("JerkgramBlockedReactionPolicy.isMessageHidden(" in entries, "chat history does not filter blocked message authors")
    require("authorId: message.author?.id" in entries, "chat history author binding missing")
    require(entries.index("JerkgramBlockedReactionPolicy.isMessageHidden(") < entries.index("count += 1"), "blocked message is counted before filtering")

    require(history_list.count(HISTORY_REFRESH_MARKER) == 1, "chat history visibility-refresh marker count")
    require("JerkgramBlockedReactionPolicy.presentationUpdates" in history_list, "chat history is not subscribed to visibility changes")
    require("let historyViewUpdateValue = combineLatest(" in history_list, "visibility refresh is not joined to history updates")


def main() -> None:
    owners = (BLOCKED_CONTEXT, STORE_MESSAGE, ACCOUNT_VIEW_TRACKER, DELETE_MESSAGES, CHAT_LIST, NAVIGATION, CHAT_HISTORY_ENTRIES, CHAT_HISTORY_LIST)
    for path in owners:
        require(path.is_file(), "missing source owner: " + str(path))

    verify_policy(BLOCKED_CONTEXT.read_text(encoding="utf-8"))
    verify_store_owner(STORE_MESSAGE.read_text(encoding="utf-8"))
    verify_refresh_owners(
        ACCOUNT_VIEW_TRACKER.read_text(encoding="utf-8"),
        DELETE_MESSAGES.read_text(encoding="utf-8"),
    )
    verify_chat_list_owner(CHAT_LIST.read_text(encoding="utf-8"))
    verify_navigation_owner(NAVIGATION.read_text(encoding="utf-8"))
    verify_chat_history_owners(
        CHAT_HISTORY_ENTRIES.read_text(encoding="utf-8"),
        CHAT_HISTORY_LIST.read_text(encoding="utf-8"),
    )
    print("[Build133 blocked activity verifier] PREFLIGHT OWNER CHECKS GREEN")


if __name__ == "__main__":
    main()
