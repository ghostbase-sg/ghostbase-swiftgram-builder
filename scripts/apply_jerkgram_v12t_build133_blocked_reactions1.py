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

POLICY_MARKER = "// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_POLICY1"
ATTRIBUTE_MARKER = "// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_AGGREGATE1"
LIST_MARKER = "// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_LIST1"
ACCOUNT_MARKER = "// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_OBSERVER1"
UI_MARKER = "// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_UI1"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 blocked reactions] " + message)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    require(count == 1, f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def filter_reaction_model(reactions, recent_peers, blocked_peer_ids, account_peer_id, enabled=True):
    """Pure contract model used by Build133 tests.

    reactions: [(value, count, is_own)]
    recent_peers: [(value, peer_id|None, is_own)]
    """
    if not enabled or not blocked_peer_ids:
        return list(reactions), list(recent_peers)

    visible_reactions = [list(item) for item in reactions]
    visible_recent = []

    for value, peer_id, is_own in recent_peers:
        is_known_blocked = (
            peer_id is not None
            and peer_id != account_peer_id
            and not is_own
            and peer_id in blocked_peer_ids
        )
        if not is_known_blocked:
            visible_recent.append((value, peer_id, is_own))
            continue

        for index, item in enumerate(visible_reactions):
            if item[0] != value:
                continue
            minimum = 1 if item[2] else 0
            item[1] = max(minimum, item[1] - 1)
            if item[1] == 0:
                visible_reactions.pop(index)
            break

    return [tuple(item) for item in visible_reactions], visible_recent


POLICY_SOURCE = r'''

// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_POLICY1
// A single per-account O(1) presentation cache. The server/Postbox reaction
// attributes remain untouched; only presentation owners consult this policy.
public enum JerkgramBlockedReactionPolicy {
    public static let hideBlockedReactionsKey = "jerkgram.Messages.HideBlockedReactions"
    public static let hideBlockedMessagesKey = "jerkgram.Messages.HideBlockedMessages"

    private static let blockedPeerIdsByAccount = Atomic(value: [PeerId: Set<PeerId>]())

    public static func replaceBlockedPeerIds(accountPeerId: PeerId, peerIds: Set<PeerId>) {
        let _ = self.blockedPeerIdsByAccount.modify { current in
            var current = current
            current[accountPeerId] = peerIds
            return current
        }
    }

    public static func blockedPeerIds(accountPeerId: PeerId) -> Set<PeerId> {
        return self.blockedPeerIdsByAccount.with { current in
            return current[accountPeerId] ?? Set()
        }
    }

    public static func isBlocked(accountPeerId: PeerId, peerId: PeerId) -> Bool {
        return self.blockedPeerIdsByAccount.with { current in
            return current[accountPeerId]?.contains(peerId) ?? false
        }
    }

    public static func hideBlockedReactions(accountPeerId: PeerId) -> Bool {
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
}

// Retained once per live AccountContext. It owns the normal Telegram
// BlockedPeersContext and drains all pages; there is no request per message.
public final class JerkgramBlockedPeersObserver {
    private let context: BlockedPeersContext
    private let disposable = MetaDisposable()

    public init(account: Account) {
        assert(Queue.mainQueue().isCurrent())
        let context = BlockedPeersContext(account: account, subject: .blocked)
        self.context = context
        self.disposable.set((context.state
        |> deliverOnMainQueue).start(next: { state in
            JerkgramBlockedReactionPolicy.replaceBlockedPeerIds(
                accountPeerId: account.peerId,
                peerIds: Set(state.peers.map { $0.peerId })
            )
            if state.canLoadMore && !state.isLoadingMore {
                Queue.mainQueue().async {
                    context.loadMore()
                }
            }
        }))
    }

    deinit {
        self.disposable.dispose()
    }
}
'''


ATTRIBUTE_HELPER = r'''

// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_AGGREGATE1
// Filter only actors whose identity is reliably known. Unknown/anonymous
// contributions are intentionally preserved. The original attribute is never
// mutated, so disabling the feature restores stock state immediately.
public func jerkgramFilteredMessageReactions(
    accountPeerId: EnginePeer.Id,
    attribute: ReactionsMessageAttribute?
) -> ReactionsMessageAttribute? {
    guard let attribute else {
        return nil
    }
    guard JerkgramBlockedReactionPolicy.hideBlockedReactions(accountPeerId: accountPeerId) else {
        return attribute
    }
    let blockedPeerIds = JerkgramBlockedReactionPolicy.blockedPeerIds(accountPeerId: accountPeerId)
    if blockedPeerIds.isEmpty {
        return attribute
    }

    var reactions = attribute.reactions
    var recentPeers: [ReactionsMessageAttribute.RecentPeer] = []

    for recentPeer in attribute.recentPeers {
        let isOwn = recentPeer.isMy || recentPeer.peerId == accountPeerId
        if !isOwn && blockedPeerIds.contains(recentPeer.peerId) {
            if let index = reactions.firstIndex(where: { $0.value == recentPeer.value }) {
                let current = reactions[index]
                let minimumCount: Int32 = current.chosenOrder == nil ? 0 : 1
                let updatedCount = max(minimumCount, current.count - 1)
                if updatedCount == 0 {
                    reactions.remove(at: index)
                } else {
                    reactions[index] = MessageReaction(
                        value: current.value,
                        count: updatedCount,
                        chosenOrder: current.chosenOrder
                    )
                }
            }
        } else {
            recentPeers.append(recentPeer)
        }
    }

    let topPeers = attribute.topPeers.filter { item in
        if item.isMy || item.isAnonymous {
            return true
        }
        guard let peerId = item.peerId else {
            return true
        }
        return !blockedPeerIds.contains(peerId)
    }

    if reactions.isEmpty {
        return nil
    }
    return ReactionsMessageAttribute(
        canViewList: attribute.canViewList,
        isTags: attribute.isTags,
        reactions: reactions,
        recentPeers: recentPeers,
        topPeers: topPeers
    )
}

public func jerkgramVisibleMessageReactions(
    accountPeerId: EnginePeer.Id,
    attributes: [MessageAttribute],
    isTags: Bool
) -> ReactionsMessageAttribute? {
    return jerkgramFilteredMessageReactions(
        accountPeerId: accountPeerId,
        attribute: mergedMessageReactions(attributes: attributes, isTags: isTags)
    )
}
'''


def patch_blocked_context(text: str) -> str:
    if POLICY_MARKER in text:
        require(text.count(POLICY_MARKER) == 1, "policy marker is ambiguous")
        return text

    class_anchor = "public final class BlockedPeersContext {"
    require(text.count(class_anchor) == 1, "BlockedPeersContext owner is missing or ambiguous")
    text = text.replace(class_anchor, POLICY_SOURCE + "\n" + class_anchor, 1)

    old = '''        didSet {
            if self._state != oldValue {
                self._statePromise.set(.single(self._state))
            }
        }'''
    new = '''        didSet {
            if self._state != oldValue {
                self._statePromise.set(.single(self._state))
                if case .blocked = self.subject {
                    JerkgramBlockedReactionPolicy.replaceBlockedPeerIds(
                        accountPeerId: self.account.peerId,
                        peerIds: Set(self._state.peers.map { $0.peerId })
                    )
                }
            }
        }'''
    text = replace_once(text, old, new, "BlockedPeersContext state publication")
    return text


def patch_account_context(text: str) -> str:
    if ACCOUNT_MARKER in text:
        require(text.count(ACCOUNT_MARKER) == 1, "account observer marker is ambiguous")
        return text

    property_anchor = '''    public let account: Account
    public let engine: TelegramEngine
'''
    property_replacement = '''    public let account: Account
    public let engine: TelegramEngine
    // MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_OBSERVER1
    private let jerkgramBlockedPeersObserver: JerkgramBlockedPeersObserver?
'''
    text = replace_once(text, property_anchor, property_replacement, "AccountContext observer property")

    init_anchor = '''        self.account = account
        self.engine = TelegramEngine(account: account)
        
        self.imageCache = DirectMediaImageCache(account: account)
'''
    init_replacement = '''        self.account = account
        self.engine = TelegramEngine(account: account)
        self.jerkgramBlockedPeersObserver = sharedContext.applicationBindings.isMainApp && !temp
            ? JerkgramBlockedPeersObserver(account: account)
            : nil
        
        self.imageCache = DirectMediaImageCache(account: account)
'''
    text = replace_once(text, init_anchor, init_replacement, "AccountContext observer initialization")
    return text


def patch_reaction_attribute(text: str) -> str:
    if ATTRIBUTE_MARKER in text:
        require(text.count(ATTRIBUTE_MARKER) == 1, "aggregate marker is ambiguous")
        return text

    owner = "public func mergedMessageReactionsAndPeers(accountPeerId: EnginePeer.Id, accountPeer: EnginePeer?, message: Message)"
    require(text.count(owner) == 1, "mergedMessageReactionsAndPeers owner is missing or ambiguous")

    insert_anchor = "\npublic func mergedMessageReactionsAndPeers(accountPeerId: EnginePeer.Id, accountPeer: EnginePeer?, message: Message)"
    require(text.count(insert_anchor) == 1, "aggregate helper insertion anchor is missing or ambiguous")
    text = text.replace(insert_anchor, ATTRIBUTE_HELPER + insert_anchor, 1)

    old_guard = '''    guard let attribute = mergedMessageReactions(attributes: message.attributes, isTags: message.areReactionsTags(accountPeerId: accountPeerId)) else {'''
    new_guard = '''    guard let attribute = jerkgramVisibleMessageReactions(accountPeerId: accountPeerId, attributes: message.attributes, isTags: message.areReactionsTags(accountPeerId: accountPeerId)) else {'''
    text = replace_once(text, old_guard, new_guard, "merged reactions presentation guard")
    return text


def patch_reaction_list(text: str) -> str:
    if LIST_MARKER in text:
        require(text.count(LIST_MARKER) == 1, "reaction list marker is ambiguous")
        return text

    old_signature = '''public extension EngineMessageReactionListContext.State {
    init(message: EngineMessage, readStats: MessageReadStats?, reaction: MessageReaction.Reaction?) {'''
    new_signature = '''// MARK: Jerkgram v1.2T BUILD133_BLOCKED_REACTION_LIST1
public extension EngineMessageReactionListContext.State {
    init(message: EngineMessage, readStats: MessageReadStats?, reaction: MessageReaction.Reaction?, accountPeerId: PeerId? = nil) {'''
    text = replace_once(text, old_signature, new_signature, "reaction list State initializer")

    old_attr = '''        if let reactionsAttribute = message._asMessage().reactionsAttribute {
            for messageReaction in reactionsAttribute.reactions {'''
    new_attr = '''        let reactionsAttribute: ReactionsMessageAttribute?
        if let accountPeerId {
            reactionsAttribute = jerkgramFilteredMessageReactions(
                accountPeerId: accountPeerId,
                attribute: message._asMessage().reactionsAttribute
            )
        } else {
            reactionsAttribute = message._asMessage().reactionsAttribute
        }
        if let reactionsAttribute {
            for messageReaction in reactionsAttribute.reactions {'''
    text = replace_once(text, old_attr, new_attr, "reaction list filtered attribute")

    old_initial = "let initialState = EngineMessageReactionListContext.State(message: message, readStats: readStats, reaction: reaction)"
    new_initial = "let initialState = EngineMessageReactionListContext.State(message: message, readStats: readStats, reaction: reaction, accountPeerId: account.peerId)"
    text = replace_once(text, old_initial, new_initial, "reaction list initial account policy")

    old_items = '''                            var items: [EngineMessageReactionListContext.Item] = []
                            for reaction in reactions {
                                switch reaction {
                                case let .messagePeerReaction(messagePeerReactionData):
                                    let (peer, date, reaction) = (messagePeerReactionData.peerId, messagePeerReactionData.date, messagePeerReactionData.reaction)
                                    if let peer = transaction.getPeer(peer.peerId), let reaction = MessageReaction.Reaction(apiReaction: reaction) {
                                        items.append(EngineMessageReactionListContext.Item(peer: EnginePeer(peer), reaction: reaction, timestamp: date, timestampIsReaction: true))
                                    }
                                }
                            }
                            
                            return InternalState(hasOutgoingReaction: false, totalCount: Int(count), items: items, canLoadMore: nextOffset != nil, nextOffset: nextOffset)'''
    new_items = '''                            var items: [EngineMessageReactionListContext.Item] = []
                            var blockedItemsOnPage = 0
                            let filterBlocked = JerkgramBlockedReactionPolicy.hideBlockedReactions(accountPeerId: accountPeerId)
                            for reaction in reactions {
                                switch reaction {
                                case let .messagePeerReaction(messagePeerReactionData):
                                    let (peer, date, reaction) = (messagePeerReactionData.peerId, messagePeerReactionData.date, messagePeerReactionData.reaction)
                                    let peerId = peer.peerId
                                    if filterBlocked && peerId != accountPeerId && JerkgramBlockedReactionPolicy.isBlocked(accountPeerId: accountPeerId, peerId: peerId) {
                                        blockedItemsOnPage += 1
                                        continue
                                    }
                                    if let peer = transaction.getPeer(peerId), let reaction = MessageReaction.Reaction(apiReaction: reaction) {
                                        items.append(EngineMessageReactionListContext.Item(peer: EnginePeer(peer), reaction: reaction, timestamp: date, timestampIsReaction: true))
                                    }
                                }
                            }
                            let visibleTotalCount = max(0, Int(count) - blockedItemsOnPage)
                            return InternalState(hasOutgoingReaction: false, totalCount: visibleTotalCount, items: items, canLoadMore: nextOffset != nil, nextOffset: nextOffset)'''
    text = replace_once(text, old_items, new_items, "network reaction list filtering")
    return text


def patch_direct_ui_owner(text: str, path: Path) -> str:
    if UI_MARKER in text:
        return text

    old = "mergedMessageReactions(attributes: item.message.attributes, isTags: item.message.areReactionsTags(accountPeerId: item.context.account.peerId))"
    count = text.count(old)
    require(count == 1, f"{path.name}: expected one direct presentation call, found {count}")
    new = "jerkgramVisibleMessageReactions(accountPeerId: item.context.account.peerId, attributes: item.message.attributes, isTags: item.message.areReactionsTags(accountPeerId: item.context.account.peerId))"
    text = text.replace(old, new, 1)

    import_anchor = "import TelegramCore\n"
    require(text.count(import_anchor) >= 1, f"{path.name}: TelegramCore import missing")
    text = text.replace(import_anchor, import_anchor + UI_MARKER + "\n", 1)
    return text


def main() -> None:
    for path in (REACTION_ATTRIBUTE, REACTION_LIST, BLOCKED_CONTEXT, ACCOUNT_CONTEXT, *DIRECT_UI_OWNERS):
        require(path.is_file(), "missing source owner: " + str(path))

    BLOCKED_CONTEXT.write_text(patch_blocked_context(BLOCKED_CONTEXT.read_text(encoding="utf-8")), encoding="utf-8")
    ACCOUNT_CONTEXT.write_text(patch_account_context(ACCOUNT_CONTEXT.read_text(encoding="utf-8")), encoding="utf-8")
    REACTION_ATTRIBUTE.write_text(patch_reaction_attribute(REACTION_ATTRIBUTE.read_text(encoding="utf-8")), encoding="utf-8")
    REACTION_LIST.write_text(patch_reaction_list(REACTION_LIST.read_text(encoding="utf-8")), encoding="utf-8")

    for path in DIRECT_UI_OWNERS:
        path.write_text(patch_direct_ui_owner(path.read_text(encoding="utf-8"), path), encoding="utf-8")

    print("[Build133 blocked reactions] SOURCE PATCHED")


if __name__ == "__main__":
    main()
