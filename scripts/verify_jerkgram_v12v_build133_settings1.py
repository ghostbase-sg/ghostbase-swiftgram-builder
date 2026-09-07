#!/usr/bin/env python3

from pathlib import Path
import os
import re


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
SETTINGS = ROOT / "submodules/SettingsUI/Sources/GhostBase/GhostBaseSettingsController.swift"
STRINGS = ROOT / "submodules/TelegramPresentationData/Sources/JerkgramStrings.swift"

MARKER = "// MARK: Jerkgram v1.2V BUILD133_BLOCKED_SETTINGS1"
STRINGS_MARKER = "// MARK: Jerkgram v1.2V BUILD133_BLOCKED_SETTINGS_STRINGS1"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 Settings verifier] " + message)


def block_bounds(text: str, signature: str) -> tuple[int, int]:
    start = text.find(signature)
    require(start >= 0, "block missing: " + signature)
    brace = text.find("{", start)
    require(brace >= 0, "opening brace missing: " + signature)
    depth = 0
    in_string = False
    escaped = False
    for index in range(brace, len(text)):
        ch = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1
    raise RuntimeError("[Build133 Settings verifier] unbalanced block: " + signature)


def verify_strings(text: str) -> None:
    require(text.count(STRINGS_MARKER) == 1, "strings marker count != 1")
    require('var blockedUsers: String' in text, "blockedUsers semantic key missing")
    require('var hideBlockedMessages: String' in text, "hideBlockedMessages semantic key missing")
    require('var hideBlockedReactions: String' in text, "hideBlockedReactions semantic key missing")
    require('"BLOCKED USERS"' in text, "canonical English blocked header missing")
    require('"Hide Blocked Messages"' in text, "canonical English blocked-message title missing")
    require('"Hide Blocked Reactions"' in text, "canonical English blocked-reaction title missing")
    require('"ЗАБЛОКИРОВАННЫЕ"' in text, "Russian blocked header missing")
    require('"Скрывать сообщения заблокированных"' in text, "Russian blocked-message title missing")
    require('"Скрывать реакции заблокированных"' in text, "Russian blocked-reaction title missing")
    require("languageCode" in text, "Telegram language-backed JerkgramStrings languageCode missing")
    require("Locale.current" not in text[text.index(STRINGS_MARKER):], "Build133 strings must not consult iOS Locale.current")


def verify_settings(text: str) -> None:
    require(text.count(MARKER) == 1, "Settings marker count != 1")
    require(text.count('static let hideBlockedMessages = "jerkgram.Messages.HideBlockedMessages"') == 1, "blocked-message storage key count != 1")
    require(text.count('static let hideBlockedReactions = "jerkgram.Messages.HideBlockedReactions"') == 1, "blocked-reaction storage key count != 1")
    require("var hideBlockedMessages: Bool" in text, "blocked-message state missing")
    require("var hideBlockedReactions: Bool" in text, "blocked-reaction state missing")
    require("updated.hideBlockedMessages = value" in text, "blocked-message update case missing")
    require("updated.hideBlockedReactions = value" in text, "blocked-reaction update case missing")
    sync_start = text.find("let jerkgramSynchronousRuntimeSettingKeys: Set<String> = [")
    require(sync_start >= 0, "synchronous runtime key owner missing")
    sync_end = text.find("\n    ]", sync_start)
    require(sync_end >= 0, "synchronous runtime key owner is unbalanced")
    synchronous_keys = text[sync_start:sync_end]
    require("GhostBaseKey.hideBlockedMessages," in synchronous_keys, "blocked-message synchronous key missing")
    require("GhostBaseKey.hideBlockedReactions," in synchronous_keys, "blocked-reaction synchronous key missing")
    require(text.count("JerkgramBlockedReactionPolicy.notifySettingsChanged()") == 1, "blocked runtime refresh notification count != 1")
    persistence_start, persistence_end = block_bounds(text, "private func jerkgramPersistChangedSettings(")
    persistence = text[persistence_start:persistence_end]
    require(
        persistence.index("value.write(to: defaults, key: key)")
        < persistence.index("JerkgramBlockedReactionPolicy.notifySettingsChanged()"),
        "runtime refresh fires before blocked settings are committed",
    )

    start, end = block_bounds(text, "if page == .messages {")
    messages = text[start:end]
    require(messages.count("strings.blockedUsers") == 1, "blocked section header count != 1")
    require(messages.count("strings.hideBlockedMessages") == 1, "blocked-message row count != 1")
    require(messages.count("strings.hideBlockedReactions") == 1, "blocked-reaction row count != 1")

    # Guard the exact Build133 regression that reached Swift compilation: the
    # preexisting last row already had a trailing comma and the patch emitted a
    # second standalone comma before the new blocked-users header.
    require(
        re.search(r",\s*,\s*\.header\(\d+,\s*strings\.blockedUsers\)", messages) is None,
        "duplicate/standalone comma before blocked section",
    )

    header = re.search(r"\.header\((\d+),\s*strings\.blockedUsers\)", messages)
    blocked_messages = re.search(r"\.toggle\((\d+),\s*1,\s*GhostBaseKey\.hideBlockedMessages", messages)
    blocked_reactions = re.search(r"\.toggle\((\d+),\s*2,\s*GhostBaseKey\.hideBlockedReactions", messages)
    require(header is not None and blocked_messages is not None and blocked_reactions is not None, "blocked native rows malformed")
    require(header.group(1) == blocked_messages.group(1) == blocked_reactions.group(1), "blocked rows do not share their own section")

    other_sections = [
        int(value)
        for value in re.findall(r"\.header\((\d+),", messages)
        if value != header.group(1)
    ]
    require(not other_sections or int(header.group(1)) > max(other_sections), "blocked section is not a late independent Messages section")

    for literal in (
        "ЗАБЛОКИРОВАННЫЕ",
        "Скрывать сообщения заблокированных",
        "Скрывать реакции заблокированных",
    ):
        require(literal not in text, "hard-coded Cyrillic leaked into active Settings owner: " + literal)

    # Existing entry renderer must remain the native Telegram switch item.
    require("ItemListSwitchItem(" in text, "native ItemListSwitchItem renderer missing")
    require("case let .toggle" in text, "native toggle entry renderer missing")
    forbidden = (
        "UISwitch(",
        "switch.frame",
        "switchNode.frame",
        "titleLabel.frame",
        "label.frame",
        "width: 240",
        "fontSize: 12",
        "minimumScaleFactor",
    )
    for token in forbidden:
        require(token not in messages, "manual/fixed blocked-row layout detected: " + token)


def main() -> None:
    require(SETTINGS.is_file(), "Settings materialized owner missing")
    require(STRINGS.is_file(), "JerkgramStrings materialized owner missing")
    verify_strings(STRINGS.read_text(encoding="utf-8"))
    verify_settings(SETTINGS.read_text(encoding="utf-8"))
    print("[Build133 Settings verifier] PREFLIGHT GREEN")


if __name__ == "__main__":
    main()
