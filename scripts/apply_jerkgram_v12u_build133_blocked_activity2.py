#!/usr/bin/env python3

import re

import apply_jerkgram_v12u_build133_blocked_activity1 as base


TARGET_FUNCTIONS = (
    "func _internal_deleteAllReactionsWithAuthor(",
    "func _internal_deleteReaction(",
)

OWNER_PATTERN = re.compile(
    r"(?m)^(?P<indent>[ \t]*)var tags = currentMessage\.tags\n"
    r"(?P=indent)if attributes\.contains\(where: \{ \(\$0 as\? ReactionsMessageAttribute\)\?\.hasUnseen == true \}\) \{\n"
    r"(?P=indent)    tags\.insert\(\.unseenReaction\)\n"
    r"(?P=indent)\} else \{\n"
    r"(?P=indent)    tags\.remove\(\.unseenReaction\)\n"
    r"(?P=indent)\}"
)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 blocked activity2] " + message)


def function_slice(text: str, signature: str) -> tuple[int, int]:
    start = text.find(signature)
    require(start >= 0, "missing DeleteMessages owner: " + signature)
    next_func = text.find("\nfunc ", start + len(signature))
    end = len(text) if next_func < 0 else next_func
    return start, end


def replacement(indent: str) -> str:
    return (
        f"{indent}// MARK: Jerkgram v1.2U BUILD133_BLOCKED_ACTIVITY_DELETE1\n"
        f"{indent}var tags = currentMessage.tags\n"
        f"{indent}let hasVisibleUnseenReaction = attributes.compactMap {{ $0 as? ReactionsMessageAttribute }}.contains(where: {{\n"
        f"{indent}    JerkgramBlockedReactionPolicy.hasVisibleUnseenReaction(\n"
        f"{indent}        accountPeerId: account.peerId,\n"
        f"{indent}        message: currentMessage,\n"
        f"{indent}        attribute: $0\n"
        f"{indent}    )\n"
        f"{indent}}})\n"
        f"{indent}if hasVisibleUnseenReaction {{\n"
        f"{indent}    tags.insert(.unseenReaction)\n"
        f"{indent}}} else {{\n"
        f"{indent}    tags.remove(.unseenReaction)\n"
        f"{indent}}}"
    )


def patch_delete_messages(text: str) -> str:
    if base.DELETE_MARKER in text:
        require(text.count(base.DELETE_MARKER) == 2, "DeleteMessages marker count mismatch")
        return text

    # Both semantic owners are mandatory. They differ only in indentation after
    # the historical chain, so patch each function independently and fail closed.
    for signature in TARGET_FUNCTIONS:
        start, end = function_slice(text, signature)
        owner = text[start:end]
        matches = list(OWNER_PATTERN.finditer(owner))
        require(len(matches) == 1, f"{signature}: expected one unseen-reaction tag owner, found {len(matches)}")
        match = matches[0]
        updated_owner = owner[:match.start()] + replacement(match.group("indent")) + owner[match.end():]
        text = text[:start] + updated_owner + text[end:]

    require(text.count(base.DELETE_MARKER) == 2, "DeleteMessages patched marker count != 2")
    require("attributes.contains(where: { ($0 as? ReactionsMessageAttribute)?.hasUnseen == true })" not in "\n".join(
        text[s:e] for s, e in (function_slice(text, signature) for signature in TARGET_FUNCTIONS)
    ), "stock unseen-reaction tag owner survived in targeted functions")
    return text


def main() -> None:
    # Reuse every proven v12u owner/patch from activity1, replacing only the
    # DeleteMessages matcher that was too indentation-specific.
    base.patch_delete_messages = patch_delete_messages
    base.main()
    print("[Build133 blocked activity2] DeleteMessages semantic-owner matcher GREEN")


if __name__ == "__main__":
    main()
