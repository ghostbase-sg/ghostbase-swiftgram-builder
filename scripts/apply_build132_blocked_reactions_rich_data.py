#!/usr/bin/env python3
from pathlib import Path

TARGET = Path("materialized/telegram-ios/submodules/TelegramCore/Sources/State/AccountStateManager.swift")
MARKER = "jerkgram_build132_blocked_reactions_rich_data_v1"

def main():
    if not TARGET.exists():
        raise SystemExit(f"missing {TARGET}")
    text = TARGET.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched")
        return

    anchor = """                        let author = transaction.getPeer(postboxMessage.author.id)"""
    if anchor not in text:
        raise SystemExit("rich_data anchor not found")
    replacement = """                        // jerkgram_build132_blocked_reactions_rich_data_v1
                        let jerkgramBuild132HideBlockedReactionPayload = (UserDefaults.standard.object(forKey: "jerkgram.Messages.HideBlockedReactions") as? Bool) ?? true
                        if jerkgramBuild132HideBlockedReactionPayload && postbox.blockedPeerStatusTable.get(postboxMessage.author.id).value == true {
                            continue
                        }
                        let author = transaction.getPeer(postboxMessage.author.id)"""
    text = text.replace(anchor, replacement, 1)
    TARGET.write_text(text, encoding="utf-8")
    print("patched AccountStateManager rich data")

if __name__ == "__main__":
    main()
