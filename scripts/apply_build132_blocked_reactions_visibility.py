#!/usr/bin/env python3
from pathlib import Path

ROOT = Path("materialized/telegram-ios")
MESSAGE_REACTIONS = ROOT / "submodules/TelegramUI/Sources/Components/MessageReactions/MessageReactions.swift"
SETTINGS = ROOT / "Telegram/Settings/GhostBaseSettings.swift"


def patch_message_reactions():
    if not MESSAGE_REACTIONS.exists():
        raise SystemExit(f"[Build132 blocked reactions] missing {MESSAGE_REACTIONS}")
    text = MESSAGE_REACTIONS.read_text(encoding="utf-8")

    marker = "jerkgram_build132_blocked_reactions_v1"
    if marker in text:
        print("[Build132 blocked reactions] MessageReactions already patched")
        return

    old = """        let availablePeers = item.availablePeers
        let availableReactions = item.availableReactions"""
    new = f"""        // {marker}
        let jerkgramBuild132HideBlockedReactions = (UserDefaults.standard.object(forKey: "jerkgram.Messages.HideBlockedReactions") as? Bool) ?? true
        let jerkgramBuild132Postbox = item.context.account.postbox
        let availablePeers = item.availablePeers.filter {{ peer in
            if !jerkgramBuild132HideBlockedReactions {{
                return true
            }}
            if peer.id == item.context.account.peerId {{
                return true
            }}
            let jerkgramBuild132Status = jerkgramBuild132Postbox.blockedPeerStatusTable.get(peer.id)
            return jerkgramBuild132Status.value != true
        }}
        let availableReactions = item.availableReactions"""

    if old not in text:
        raise SystemExit("[Build132 blocked reactions] MessageReactions anchor not found")
    text = text.replace(old, new, 1)
    MESSAGE_REACTIONS.write_text(text, encoding="utf-8")
    print("[Build132 blocked reactions] patched MessageReactions.swift")


def patch_settings():
    if not SETTINGS.exists():
        raise SystemExit(f"[Build132 blocked reactions] missing {SETTINGS}")
    text = SETTINGS.read_text(encoding="utf-8")

    if 'var hideBlockedReactions: Bool = true' not in text:
        anchor = """    var ghostHideTyping: Bool = false
    var jailbreak: String = ""
}"""
        replacement = """    var ghostHideTyping: Bool = false
    var hideBlockedReactions: Bool = true
    var jailbreak: String = ""
}"""
        if anchor not in text:
            raise SystemExit("[Build132 blocked reactions] GhostBaseState anchor not found")
        text = text.replace(anchor, replacement, 1)

    if 'values["jerkgram.Messages.HideBlockedReactions"] = state.hideBlockedReactions' not in text:
        anchor = """        values["jerkgram.GhostMode.HideTyping"] = state.ghostHideTyping
        jerkgramPersistScopedSettingValues(accountPeerId: self.context.account.peerId.toInt64(), values: values)"""
        replacement = """        values["jerkgram.GhostMode.HideTyping"] = state.ghostHideTyping
        values["jerkgram.Messages.HideBlockedReactions"] = state.hideBlockedReactions
        UserDefaults.standard.set(state.hideBlockedReactions, forKey: "jerkgram.Messages.HideBlockedReactions")
        jerkgramPersistScopedSettingValues(accountPeerId: self.context.account.peerId.toInt64(), values: values)"""
        if anchor not in text:
            raise SystemExit("[Build132 blocked reactions] settings persistence anchor not found")
        text = text.replace(anchor, replacement, 1)

    if 'case .messageHideBlockedReactions:' not in text:
        anchor = """        case .ghostHideTyping:
            self.updateState { $0.ghostHideTyping = value }
        default:"""
        replacement = """        case .ghostHideTyping:
            self.updateState { $0.ghostHideTyping = value }
        case .messageHideBlockedReactions:
            self.updateState { $0.hideBlockedReactions = value }
        default:"""
        if anchor not in text:
            raise SystemExit("[Build132 blocked reactions] switch toggle anchor not found")
        text = text.replace(anchor, replacement, 1)

    if 'hideBlockedReactions:' not in text:
        anchor = """            ghostHideTyping: jerkgramGetScopedBool(accountPeerId: self.context.account.peerId.toInt64(), key: "jerkgram.GhostMode.HideTyping", fallback: "telegram.user.defaults", defaultValue: false),
            jailbreak:"""
        replacement = """            ghostHideTyping: jerkgramGetScopedBool(accountPeerId: self.context.account.peerId.toInt64(), key: "jerkgram.GhostMode.HideTyping", fallback: "telegram.user.defaults", defaultValue: false),
            hideBlockedReactions: jerkgramGetScopedBool(accountPeerId: self.context.account.peerId.toInt64(), key: "jerkgram.Messages.HideBlockedReactions", fallback: "telegram.user.defaults", defaultValue: true),
            jailbreak:"""
        if anchor not in text:
            raise SystemExit("[Build132 blocked reactions] scoped initial state anchor not found")
        text = text.replace(anchor, replacement, 1)

    if 'case messageHideBlockedReactions' not in text:
        anchor = """    case messageEditHistory(Int32)
    case storyTimeMachine(Int32)"""
        replacement = """    case messageEditHistory(Int32)
    case messageHideBlockedReactions(Int32)
    case storyTimeMachine(Int32)"""
        if anchor not in text:
            raise SystemExit("[Build132 blocked reactions] entry enum anchor not found")
        text = text.replace(anchor, replacement, 1)

    if 'case .messageHideBlockedReactions:' not in text:
        raise SystemExit("[Build132 blocked reactions] internal switch case missing after patch")

    if 'case let .messageHideBlockedReactions(sectionId):' not in text:
        anchor = """            case let .messageEditHistory(sectionId):
                return TelegramPresentationData.ItemList.Item(title: presentationData.strings.Settings_EditHistory, sectionId: sectionId, style: .blocks)"""
        replacement = """            case let .messageEditHistory(sectionId):
                return TelegramPresentationData.ItemList.Item(title: presentationData.strings.Settings_EditHistory, sectionId: sectionId, style: .blocks)
            case let .messageHideBlockedReactions(sectionId):
                return TelegramPresentationData.ItemList.SwitchItem(
                    title: presentationData.strings.Jerkgram_Settings_HideBlockedReactions,
                    value: state.hideBlockedReactions,
                    sectionId: sectionId,
                    style: .blocks,
                    action: { value in
                        arguments.updateSwitchEntry(.messageHideBlockedReactions(sectionId), value: value)
                    }
                )"""
        if anchor not in text:
            raise SystemExit("[Build132 blocked reactions] settings item anchor not found")
        text = text.replace(anchor, replacement, 1)

    settings_anchor = """        entries.append(.messageEditHistory(sectionId))
        entries.append(.messageShowFallback(sectionId))"""
    settings_replacement = """        entries.append(.messageEditHistory(sectionId))
        entries.append(.messageHideBlockedReactions(sectionId))
        entries.append(.messageShowFallback(sectionId))"""
    if 'entries.append(.messageHideBlockedReactions(sectionId))' not in text:
        if settings_anchor not in text:
            raise SystemExit("[Build132 blocked reactions] settings section anchor not found")
        text = text.replace(settings_anchor, settings_replacement, 1)

    SETTINGS.write_text(text, encoding="utf-8")
    print("[Build132 blocked reactions] patched GhostBaseSettings.swift")


def main():
    patch_message_reactions()
    patch_settings()
    print("[Build132 blocked reactions] OK")


if __name__ == "__main__":
    main()
