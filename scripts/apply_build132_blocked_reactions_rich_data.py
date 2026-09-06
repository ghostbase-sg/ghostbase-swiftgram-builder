#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

OWNER = Path("submodules/TelegramUI/Components/Chat/ChatMessageRichDataBubbleContentNode/Sources/ChatMessageRichDataBubbleContentNode.swift")
MARKER = "// MARK: JERKGRAM_BUILD132_BLOCKED_REACTION_UI_FILTER"
ORIGINAL = "mergedMessageReactions(attributes: item.message.attributes, isTags: item.message.areReactionsTags(accountPeerId: item.context.account.peerId))"
WRAPPED = '''jerkgramFilteredReactionsForBlockedPeers(
                        message: item.message,
                        reactions: mergedMessageReactions(attributes: item.message.attributes, isTags: item.message.areReactionsTags(accountPeerId: item.context.account.peerId)),
                        enabled: UserDefaults.standard.bool(forKey: "jerkgram.Messages.HideBlockedReactions")
                    )'''


def fail(message: str) -> None:
    print(f"[build132-blocked-reactions-rich-data] FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_build132_blocked_reactions_rich_data.py <materialized-source-root>")
    root = Path(sys.argv[1]).expanduser().resolve()
    path = root / OWNER
    if not path.is_file():
        fail(f"missing exact owner: {OWNER}")

    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        print("[build132-blocked-reactions-rich-data] already applied")
        return

    count = text.count(ORIGINAL)
    if count < 1:
        fail(f"reaction expression missing in {OWNER}")

    text = MARKER + "\n" + text.replace(ORIGINAL, WRAPPED)
    path.write_text(text, encoding="utf-8")
    print(f"[build132-blocked-reactions-rich-data] patched expressions={count}")


if __name__ == "__main__":
    main()
