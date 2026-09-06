#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

SETTINGS = Path("submodules/SettingsUI/Sources/GhostBase/GhostBaseSettingsController.swift")
BLOCKED = Path("submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeers.swift")
BLOCKED_CONTEXT = Path("submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeersContext.swift")
REACTIONS = Path("submodules/TelegramCore/Sources/ApiUtils/ReactionsMessageAttribute.swift")
FOOTER = Path("submodules/TelegramUI/Components/Chat/ChatMessageReactionsFooterContentNode/Sources/ChatMessageReactionsFooterContentNode.swift")
STICKER = Path("submodules/TelegramUI/Components/Chat/ChatMessageStickerItemNode/Sources/ChatMessageStickerItemNode.swift")
INSTANT_VIDEO = Path("submodules/TelegramUI/Components/Chat/ChatMessageInstantVideoItemNode/Sources/ChatMessageInstantVideoItemNode.swift")
ANIMATED_STICKER = Path("submodules/TelegramUI/Components/Chat/ChatMessageAnimatedStickerItemNode/Sources/ChatMessageAnimatedStickerItemNode.swift")


def fail(message: str) -> None:
    print(f"[build132-blocked-reactions] FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def read(root: Path, rel: Path) -> str:
    path = root / rel
    if not path.is_file():
        fail(f"missing exact owner: {rel}")
    return path.read_text(encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        fail(f"expected one anchor for {label}, found {count}")
    return text.replace(old, new, 1)


def patch_settings(text: str) -> str:
    # STEP4/STEP5 visibility controls are opt-in and owned by the current
    # account-scoped Jerkgram Messages settings pipeline.
    old_default = "            hideBlockedMessages: jerkgramScopedBool(accountPeerId: accountPeerId, key: GhostBaseKey.hideBlockedMessages, defaultValue: true),\n"
    new_default = "            hideBlockedMessages: jerkgramScopedBool(accountPeerId: accountPeerId, key: GhostBaseKey.hideBlockedMessages, defaultValue: false),\n"
    if new_default not in text:
        text = replace_once(text, old_default, new_default, "hide blocked messages default OFF")

    marker = "// MARK: JERKGRAM_BUILD132_HIDE_BLOCKED_REACTIONS_SETTING"
    if marker in text:
        return text

    text = replace_once(
        text,
        '    static let hideBlockedMessages = "jerkgram.Messages.HideBlockedMessages"\n',
        '    static let hideBlockedMessages = "jerkgram.Messages.HideBlockedMessages"\n\n    // MARK: JERKGRAM_BUILD132_HIDE_BLOCKED_REACTIONS_SETTING\n    static let hideBlockedReactions = "jerkgram.Messages.HideBlockedReactions"\n',
        "reaction setting key",
    )
    text = replace_once(
        text,
        "    var hideBlockedMessages: Bool\n",
        "    var hideBlockedMessages: Bool\n    var hideBlockedReactions: Bool\n",
        "reaction state property",
    )
    text = replace_once(
        text,
        "            hideBlockedMessages: jerkgramScopedBool(accountPeerId: accountPeerId, key: GhostBaseKey.hideBlockedMessages, defaultValue: false),\n",
        "            hideBlockedMessages: jerkgramScopedBool(accountPeerId: accountPeerId, key: GhostBaseKey.hideBlockedMessages, defaultValue: false),\n            hideBlockedReactions: jerkgramScopedBool(accountPeerId: accountPeerId, key: GhostBaseKey.hideBlockedReactions, defaultValue: false),\n",
        "reaction state load OFF",
    )
    text = replace_once(
        text,
        "        GhostBaseKey.hideBlockedMessages: .bool(state.hideBlockedMessages),\n",
        "        GhostBaseKey.hideBlockedMessages: .bool(state.hideBlockedMessages),\n        GhostBaseKey.hideBlockedReactions: .bool(state.hideBlockedReactions),\n",
        "reaction state values",
    )

    message_toggle = '''            .toggle(
                1,
                90,
                GhostBaseKey.hideBlockedMessages,
                strings.languageCode == "ru" ? "Скрывать сообщения заблокированных" : "Hide blocked users' messages",
                state.hideBlockedMessages
            ),
'''
    reaction_toggle = message_toggle + '''            .toggle(
                1,
                91,
                GhostBaseKey.hideBlockedReactions,
                strings.languageCode == "ru" ? "Скрывать реакции заблокированных" : "Hide blocked users' reactions",
                state.hideBlockedReactions
            ),
'''
    text = replace_once(text, message_toggle.replace('strings.languageCode == "ru" ? "Скрывать сообщения заблокированных" : "Hide blocked users\' messages"', '"Скрывать сообщения заблокированных"'), reaction_toggle, "reaction toggle row")

    message_case = '''            case GhostBaseKey.hideBlockedMessages:
                updated.hideBlockedMessages = value
'''
    reaction_case = message_case + '''
            case GhostBaseKey.hideBlockedReactions:
                updated.hideBlockedReactions = value
                UserDefaults.standard.set(value, forKey: GhostBaseKey.hideBlockedReactions)
'''
    text = replace_once(text, message_case, reaction_case, "reaction toggle handler")
    return text


REGISTRY_SOURCE = '''// MARK: JERKGRAM_BUILD132_BLOCKED_PEER_REGISTRY
public enum JerkgramBlockedPeerRegistry {
    private static let defaultsKey = "Jerkgram.BlockedPeerIds.v1"
    private static let lock = NSLock()
    private static var blockedPeerIds: Set<PeerId> = {
        let raw = UserDefaults.standard.array(forKey: defaultsKey) as? [NSNumber] ?? []
        return Set(raw.map { PeerId($0.int64Value) })
    }()

    public static func snapshot() -> Set<PeerId> {
        lock.lock()
        let value = blockedPeerIds
        lock.unlock()
        return value
    }

    public static func setBlocked(peerId: PeerId, isBlocked: Bool) {
        lock.lock()
        if isBlocked {
            blockedPeerIds.insert(peerId)
        } else {
            blockedPeerIds.remove(peerId)
        }
        let stored = blockedPeerIds.map { NSNumber(value: $0.toInt64()) }
        lock.unlock()
        UserDefaults.standard.set(stored, forKey: defaultsKey)
    }

    public static func replaceBlockedPeerIds(_ peerIds: [PeerId]) {
        let updated = Set(peerIds)
        lock.lock()
        blockedPeerIds = updated
        let stored = updated.map { NSNumber(value: $0.toInt64()) }
        lock.unlock()
        UserDefaults.standard.set(stored, forKey: defaultsKey)
    }
}

'''


def patch_blocked(text: str) -> str:
    if "JERKGRAM_BUILD132_BLOCKED_PEER_REGISTRY" not in text:
        anchor = "func jerkgramBuild132IsGroupOrSupergroup(_ peer: Peer) -> Bool {\n"
        text = replace_once(text, anchor, REGISTRY_SOURCE + anchor, "blocked-peer registry")

    if "JerkgramBlockedPeerRegistry.setBlocked(peerId: peerId, isBlocked: isBlocked)" not in text:
        old = '''                            jerkgramBuild132UpdateBlockedAuthorVisibility(
                                transaction: transaction,
                                authorId: peerId,
                                hidden: isBlocked
                            )'''
        new = old + '''
                            JerkgramBlockedPeerRegistry.setBlocked(
                                peerId: peerId,
                                isBlocked: isBlocked
                            )'''
        text = replace_once(text, old, new, "block/unblock registry update")
    return text


def patch_blocked_context(text: str) -> str:
    marker = "// MARK: JERKGRAM_BUILD132_BLOCKED_PEER_REGISTRY_SYNC"
    if marker in text:
        return text

    anchor = '''            strongSelf._state = BlockedPeersContextState(isLoadingMore: false, canLoadMore: canLoadMore, totalCount: updatedTotalCount, peers: mergedPeers)
'''
    replacement = anchor + '''            // MARK: JERKGRAM_BUILD132_BLOCKED_PEER_REGISTRY_SYNC
            if case .blocked = strongSelf.subject {
                JerkgramBlockedPeerRegistry.replaceBlockedPeerIds(
                    mergedPeers.map { $0.peerId }
                )
            }
'''
    text = replace_once(text, anchor, replacement, "blocked-list registry sync")

    # Keep bulk list edits synchronized as well.
    bulk_anchor = '''                    strongSelf._state = BlockedPeersContextState(isLoadingMore: strongSelf._state.isLoadingMore, canLoadMore: strongSelf._state.canLoadMore, totalCount: peers.count, peers: peers.map(RenderedPeer.init))
'''
    if bulk_anchor in text and "JERKGRAM_BUILD132_BLOCKED_PEER_REGISTRY_BULK_SYNC" not in text:
        bulk_replacement = bulk_anchor + '''                    // MARK: JERKGRAM_BUILD132_BLOCKED_PEER_REGISTRY_BULK_SYNC
                    if case .blocked = strongSelf.subject {
                        JerkgramBlockedPeerRegistry.replaceBlockedPeerIds(
                            peers.map { $0.id }
                        )
                    }
'''
        text = text.replace(bulk_anchor, bulk_replacement, 1)
    return text


REACTION_HELPER = r'''// MARK: JERKGRAM_BUILD132_BLOCKED_REACTION_FILTER
public func jerkgramFilteredReactionsForBlockedPeers(
    message: Message,
    reactions: ReactionsMessageAttribute?,
    enabled: Bool
) -> ReactionsMessageAttribute? {
    guard enabled, let reactions = reactions else {
        return reactions
    }

    guard let peer = message.peers[message.id.peerId] else {
        return reactions
    }
    let isGroupOrSupergroup: Bool
    if peer is TelegramGroup {
        isGroupOrSupergroup = true
    } else if let channel = peer as? TelegramChannel, case .group = channel.info {
        isGroupOrSupergroup = true
    } else {
        isGroupOrSupergroup = false
    }
    guard isGroupOrSupergroup else {
        return reactions
    }

    let blockedPeerIds = JerkgramBlockedPeerRegistry.snapshot()
    guard !blockedPeerIds.isEmpty else {
        return reactions
    }

    var removedCounts: [MessageReaction.Reaction: Int32] = [:]
    for recentPeer in reactions.recentPeers {
        if blockedPeerIds.contains(recentPeer.peerId) {
            removedCounts[recentPeer.value, default: 0] += 1
        }
    }

    let filteredRecentPeers = reactions.recentPeers.filter {
        !blockedPeerIds.contains($0.peerId)
    }
    let filteredTopPeers = reactions.topPeers.filter { topPeer in
        guard let peerId = topPeer.peerId else {
            return true
        }
        return !blockedPeerIds.contains(peerId)
    }
    let filteredReactions = reactions.reactions.compactMap { reaction -> MessageReaction? in
        let removed = removedCounts[reaction.value] ?? 0
        let updatedCount = max(0, reaction.count - removed)
        if updatedCount == 0 && reaction.chosenOrder == nil {
            return nil
        }
        return MessageReaction(
            value: reaction.value,
            count: updatedCount,
            chosenOrder: reaction.chosenOrder
        )
    }

    if filteredRecentPeers == reactions.recentPeers
        && filteredTopPeers == reactions.topPeers
        && filteredReactions == reactions.reactions {
        return reactions
    }

    return ReactionsMessageAttribute(
        canViewList: reactions.canViewList,
        isTags: reactions.isTags,
        reactions: filteredReactions,
        recentPeers: filteredRecentPeers,
        topPeers: filteredTopPeers
    )
}

'''


def patch_reactions(text: str) -> str:
    if "JERKGRAM_BUILD132_BLOCKED_REACTION_FILTER" in text:
        return text
    anchor = "public func mergedMessageReactions(attributes: [MessageAttribute], isTags: Bool) -> ReactionsMessageAttribute? {\n"
    return replace_once(text, anchor, REACTION_HELPER + anchor, "reaction projection helper")


MERGED_PATTERN = re.compile(
    r"mergedMessageReactions\(attributes: item\.message\.attributes, isTags: item\.message\.areReactionsTags\(accountPeerId: item\.context\.account\.peerId\)\)"
)


def patch_reaction_ui(text: str, label: str) -> str:
    marker = "// MARK: JERKGRAM_BUILD132_BLOCKED_REACTION_UI_FILTER"
    if marker in text:
        return text

    matches = list(MERGED_PATTERN.finditer(text))
    if not matches:
        fail(f"no reaction-render expression found in {label}")

    original = "mergedMessageReactions(attributes: item.message.attributes, isTags: item.message.areReactionsTags(accountPeerId: item.context.account.peerId))"
    wrapped = '''jerkgramFilteredReactionsForBlockedPeers(
                    message: item.message,
                    reactions: mergedMessageReactions(attributes: item.message.attributes, isTags: item.message.areReactionsTags(accountPeerId: item.context.account.peerId)),
                    enabled: UserDefaults.standard.bool(forKey: "jerkgram.Messages.HideBlockedReactions")
                )'''
    text = text.replace(original, wrapped)
    return marker + "\n" + text


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_build132_blocked_reactions_visibility.py <materialized-source-root>")
    root = Path(sys.argv[1]).expanduser().resolve()

    owners = (SETTINGS, BLOCKED, BLOCKED_CONTEXT, REACTIONS, FOOTER, STICKER, INSTANT_VIDEO, ANIMATED_STICKER)
    originals = {rel: read(root, rel) for rel in owners}

    patched = {
        SETTINGS: patch_settings(originals[SETTINGS]),
        BLOCKED: patch_blocked(originals[BLOCKED]),
        BLOCKED_CONTEXT: patch_blocked_context(originals[BLOCKED_CONTEXT]),
        REACTIONS: patch_reactions(originals[REACTIONS]),
        FOOTER: patch_reaction_ui(originals[FOOTER], "reaction footer"),
        STICKER: patch_reaction_ui(originals[STICKER], "sticker reactions"),
        INSTANT_VIDEO: patch_reaction_ui(originals[INSTANT_VIDEO], "instant-video reactions"),
        ANIMATED_STICKER: patch_reaction_ui(originals[ANIMATED_STICKER], "animated-sticker reactions"),
    }

    # Fail closed: STEP5 must never rewrite reaction attributes in Postbox.
    if "transaction.updateMessage" in patched[REACTIONS]:
        fail("reaction projection helper unexpectedly mutates Postbox")

    changed = []
    for rel in owners:
        if patched[rel] != originals[rel]:
            (root / rel).write_text(patched[rel], encoding="utf-8")
            changed.append(str(rel))

    if changed:
        print("[build132-blocked-reactions] patched")
        for rel in changed:
            print(f"  {rel}")
    else:
        print("[build132-blocked-reactions] already applied")


if __name__ == "__main__":
    main()
