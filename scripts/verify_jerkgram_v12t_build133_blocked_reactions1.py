#!/usr/bin/env python3

from pathlib import Path
import os


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
REACTION_ATTRIBUTE = ROOT / "submodules/TelegramCore/Sources/ApiUtils/ReactionsMessageAttribute.swift"
REACTION_LIST = ROOT / "submodules/TelegramCore/Sources/State/MessageReactions.swift"
BLOCKED_CONTEXT = ROOT / "submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeersContext.swift"
ACCOUNT_CONTEXT = ROOT / "submodules/TelegramUI/Sources/AccountContext.swift"

DIRECT_UI_OWNERS = (
    ROOT / "submodules/TelegramUI/Components/Chat/ChatMessageReactionsFooterContentNode/Sources/ChatMessageReactionsFooterContentNode.swift",
    ROOT / "submodules/TelegramUI/Components/Chat/ChatMessageStickerItemNode/Sources/ChatMessageStickerItemNode.swift",
    ROOT / "submodules/TelegramUI/Components/Chat/ChatMessageInstantVideoItemNode/Sources/ChatMessageInstantVideoItemNode.swift",
    ROOT / "submodules/TelegramUI/Components/Chat/ChatMessageAnimatedStickerItemNode/Sources/ChatMessageAnimatedStickerItemNode.swift",
    ROOT / "submodules/TelegramUI/Components/Chat/ChatMessageRichDataBubbleContentNode/Sources/ChatMessageRichDataBubbleContentNode.swift",
)
BUBBLE_UI_OWNER = ROOT / "submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift"

POLICY_MARKER = "// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_POLICY1"
ATTRIBUTE_MARKER = "// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_AGGREGATE1"
LIST_MARKER = "// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_LIST1"
ACCOUNT_MARKER = "// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_OBSERVER1"
UI_MARKER = "// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_UI1"
BUBBLE_UI_MARKER = "// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_BUBBLE_UI2"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 blocked reactions verifier] " + message)


def verify_policy_source(text: str) -> None:
    require(text.count(POLICY_MARKER) == 1, "policy marker count != 1")
    require("Atomic(value: [PeerId: Set<PeerId>]())" in text, "per-account O(1) blocked set missing")
    require("JerkgramBlockedPeersObserver" in text, "retained blocked-peers observer missing")
    require("BlockedPeersContext(account: account, subject: .blocked)" in text, "Telegram blocked context is not reused")
    require("if state.canLoadMore && !state.isLoadingMore" in text, "blocked list does not drain all pages")
    require("hideBlockedReactionsKey = \"jerkgram.Messages.HideBlockedReactions\"" in text, "reaction setting key missing")
    require("return true" in text, "default blocked reaction policy missing")
    require("public static var presentationUpdates:" in text, "live presentation update signal missing")
    require("public static func notifySettingsChanged()" in text, "settings refresh bridge missing")
    require("public static func isGroupChat(_ peer: Peer?)" in text, "group-only scope owner missing")
    require("peer is TelegramGroup" in text, "legacy group scope missing")
    require("case .group = channel.info" in text, "supergroup scope missing")
    require("network.request" not in text[text.index(POLICY_MARKER):text.index("public final class BlockedPeersContext {")], "policy must not issue per-item network requests")


def verify_reaction_owner(text: str) -> None:
    require(text.count(ATTRIBUTE_MARKER) == 1, "aggregate marker count != 1")
    require("public func jerkgramFilteredMessageReactions(" in text, "filtered aggregate helper missing")
    require("message: Message" in text, "reaction filter has no chat context")
    require("JerkgramBlockedReactionPolicy.isGroupMessage(message)" in text, "reaction filter is not group-only")
    require("blockedPeerIds.contains(recentPeer.peerId)" in text, "known blocked actor membership check missing")
    require("recentPeer.isMy || recentPeer.peerId == accountPeerId" in text, "own-reaction preservation missing")
    require("if item.isMy || item.isAnonymous" in text, "anonymous/own top reactor preservation missing")
    require("let updatedCount = max(minimumCount, current.count - 1)" in text, "aggregate count decrement missing")
    require("if updatedCount == 0" in text and "reactions.remove(at: index)" in text, "zero-count pill removal missing")
    require("jerkgramVisibleMessageReactions(accountPeerId: accountPeerId" in text, "merged presentation owner does not use filtered aggregate")
    require("transaction.updateMessage" not in text[text.index(ATTRIBUTE_MARKER):text.index("private func mergeReactions")], "presentation filter must not mutate message storage")


def verify_list_owner(text: str) -> None:
    require(text.count(LIST_MARKER) == 1, "reaction list marker count != 1")
    require("accountPeerId: PeerId? = nil" in text, "reaction list account policy parameter missing")
    require("jerkgramFilteredMessageReactions(" in text, "initial details state is not filtered")
    require("accountPeerId: account.peerId" in text, "details context does not bind active account")
    require("JerkgramBlockedReactionPolicy.isBlocked(" in text, "network details page does not filter blocked peers")
    require("JerkgramBlockedReactionPolicy.isGroupMessage(message._asMessage())" in text, "network reaction list is not group-only")
    require("blockedItemsOnPage += 1" in text, "filtered page count accounting missing")
    require("let visibleTotalCount = max(0, Int(count) - blockedItemsOnPage)" in text, "details total count is not adjusted")
    require("items.count != totalCount" in text, "stock consistency gate disappeared")


def verify_account_owner(text: str) -> None:
    require(text.count(ACCOUNT_MARKER) == 1, "AccountContext observer marker count != 1")
    require("private let jerkgramBlockedPeersObserver: JerkgramBlockedPeersObserver?" in text, "observer is not retained by AccountContext")
    require("sharedContext.applicationBindings.isMainApp && !temp" in text, "observer lifecycle guard missing")


def verify_ui_owner(text: str, name: str) -> None:
    require(text.count(UI_MARKER) == 1, f"{name}: UI marker count != 1")
    require("jerkgramVisibleMessageReactions(accountPeerId:" in text, f"{name}: direct reaction presentation bypasses policy")
    require("message: item.message" in text, f"{name}: reaction presentation has no chat context")


def verify_bubble_ui_owner(text: str) -> None:
    require(text.count(BUBBLE_UI_MARKER) == 1, "standard bubble UI marker count != 1")
    require(text.count("jerkgramVisibleMessageReactions(accountPeerId:") == 2, "standard bubble does not filter both visual reaction owners")
    require("message: firstMessage" in text and "message: item.message" in text, "standard bubble reaction owners have no chat context")
    require("= mergedMessageReactions(attributes:" not in text, "standard bubble raw reaction presentation survived")


def main() -> None:
    for path in (REACTION_ATTRIBUTE, REACTION_LIST, BLOCKED_CONTEXT, ACCOUNT_CONTEXT, BUBBLE_UI_OWNER, *DIRECT_UI_OWNERS):
        require(path.is_file(), "missing materialized owner: " + str(path))

    verify_policy_source(BLOCKED_CONTEXT.read_text(encoding="utf-8"))
    verify_reaction_owner(REACTION_ATTRIBUTE.read_text(encoding="utf-8"))
    verify_list_owner(REACTION_LIST.read_text(encoding="utf-8"))
    verify_account_owner(ACCOUNT_CONTEXT.read_text(encoding="utf-8"))
    verify_bubble_ui_owner(BUBBLE_UI_OWNER.read_text(encoding="utf-8"))
    for path in DIRECT_UI_OWNERS:
        verify_ui_owner(path.read_text(encoding="utf-8"), path.name)

    print("[Build133 blocked reactions verifier] PREFLIGHT GREEN")


if __name__ == "__main__":
    main()
