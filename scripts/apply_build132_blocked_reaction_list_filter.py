#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

OWNER = Path("submodules/TelegramCore/Sources/State/MessageReactions.swift")


def fail(message: str) -> None:
    print(f"[build132-blocked-reaction-list] FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        fail(f"expected one anchor for {label}, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_build132_blocked_reaction_list_filter.py <materialized-source-root>")

    root = Path(sys.argv[1]).expanduser().resolve()
    path = root / OWNER
    if not path.is_file():
        fail(f"missing exact owner: {OWNER}")

    original = path.read_text(encoding="utf-8")
    text = original

    initial_marker = "// MARK: JERKGRAM_BUILD132_BLOCKED_REACTION_LIST_INITIAL_FILTER"
    if initial_marker not in text:
        old = '''        var items: [EngineMessageReactionListContext.Item] = []
        if let reactionsAttribute = message._asMessage().reactionsAttribute {
'''
        new = '''        var items: [EngineMessageReactionListContext.Item] = []
        // MARK: JERKGRAM_BUILD132_BLOCKED_REACTION_LIST_INITIAL_FILTER
        let jerkgramReactionsAttribute = jerkgramFilteredReactionsForBlockedPeers(
            message: message._asMessage(),
            reactions: message._asMessage().reactionsAttribute,
            enabled: UserDefaults.standard.bool(
                forKey: "jerkgram.Messages.HideBlockedReactions"
            )
        )
        if let reactionsAttribute = jerkgramReactionsAttribute {
'''
        text = replace_once(text, old, new, "initial reaction-list projection")

    page_marker = "// MARK: JERKGRAM_BUILD132_BLOCKED_REACTION_LIST_PAGE_FILTER"
    if page_marker not in text:
        old = '''                            var items: [EngineMessageReactionListContext.Item] = []
                            for reaction in reactions {
'''
        new = '''                            // MARK: JERKGRAM_BUILD132_BLOCKED_REACTION_LIST_PAGE_FILTER
                            let jerkgramShouldFilterBlockedReactionPeers: Bool
                            if UserDefaults.standard.bool(
                                forKey: "jerkgram.Messages.HideBlockedReactions"
                            ), let chatPeer = transaction.getPeer(message.id.peerId),
                               jerkgramBuild132IsGroupOrSupergroup(chatPeer) {
                                jerkgramShouldFilterBlockedReactionPeers = true
                            } else {
                                jerkgramShouldFilterBlockedReactionPeers = false
                            }
                            var jerkgramBlockedReactionPeerIds =
                                JerkgramBlockedPeerRegistry.snapshot()

                            var items: [EngineMessageReactionListContext.Item] = []
                            for reaction in reactions {
'''
        text = replace_once(text, old, new, "paginated reaction-list filter setup")

        old_append = '''                                    if let peer = transaction.getPeer(peer.peerId), let reaction = MessageReaction.Reaction(apiReaction: reaction) {
                                        items.append(EngineMessageReactionListContext.Item(peer: EnginePeer(peer), reaction: reaction, timestamp: date, timestampIsReaction: true))
                                    }
'''
        new_append = '''                                    if let peer = transaction.getPeer(peer.peerId), let reaction = MessageReaction.Reaction(apiReaction: reaction) {
                                        if jerkgramShouldFilterBlockedReactionPeers {
                                            let cachedBlocked =
                                                (transaction.getPeerCachedData(peerId: peer.id) as? CachedUserData)?.isBlocked == true
                                            if cachedBlocked && !jerkgramBlockedReactionPeerIds.contains(peer.id) {
                                                jerkgramBlockedReactionPeerIds.insert(peer.id)
                                                JerkgramBlockedPeerRegistry.setBlocked(
                                                    peerId: peer.id,
                                                    isBlocked: true
                                                )
                                            }
                                            if jerkgramBlockedReactionPeerIds.contains(peer.id) || cachedBlocked {
                                                continue
                                            }
                                        }
                                        items.append(EngineMessageReactionListContext.Item(peer: EnginePeer(peer), reaction: reaction, timestamp: date, timestampIsReaction: true))
                                    }
'''
        text = replace_once(text, old_append, new_append, "paginated blocked reactor suppression")

    if text != original:
        path.write_text(text, encoding="utf-8")
        print("[build132-blocked-reaction-list] patched")
    else:
        print("[build132-blocked-reaction-list] already applied")


if __name__ == "__main__":
    main()
