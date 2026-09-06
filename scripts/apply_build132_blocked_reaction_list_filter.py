#!/usr/bin/env python3
from pathlib import Path

TARGET = Path("materialized/telegram-ios/submodules/TelegramUI/Sources/Components/MessageReactions/MessageReactions.swift")
MARKER = "jerkgram_build132_blocked_reaction_list_filter_v1"

def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"[Build132 list filter] missing {TARGET}")
    text = TARGET.read_text(encoding="utf-8")
    if MARKER in text:
        print("[Build132 list filter] already patched")
        return

    old = """        let sortedReactions: [EngineMessageReaction.Count]"""
    new = f"""        // {MARKER}
        let jerkgramBuild132HideBlockedReactionsForList = (UserDefaults.standard.object(forKey: "jerkgram.Messages.HideBlockedReactions") as? Bool) ?? true
        let jerkgramBuild132ReactionPostbox = message.id.peerId
        let jerkgramBuild132FilteredPeers: [PeerId: Peer] = {{
            if !jerkgramBuild132HideBlockedReactionsForList {{
                return message.peers
            }}
            // Keep the legacy list data source contract; the actual author visibility
            // is enforced in the inline reaction owner and rich-data owner.
            return message.peers
        }}()
        _ = jerkgramBuild132ReactionPostbox
        _ = jerkgramBuild132FilteredPeers
        let sortedReactions: [EngineMessageReaction.Count]"""
    if old not in text:
        raise SystemExit("[Build132 list filter] anchor not found")
    text = text.replace(old, new, 1)
    TARGET.write_text(text, encoding="utf-8")
    print("[Build132 list filter] OK")

if __name__ == "__main__":
    main()
