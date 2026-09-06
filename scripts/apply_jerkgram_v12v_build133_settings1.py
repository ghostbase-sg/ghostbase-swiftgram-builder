#!/usr/bin/env python3

from pathlib import Path
import os
import re


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
SETTINGS = ROOT / "submodules/SettingsUI/Sources/GhostBase/GhostBaseSettingsController.swift"
STRINGS = ROOT / "submodules/TelegramPresentationData/Sources/JerkgramStrings.swift"

MARKER = "// MARK: Jerkgram v1.2V BUILD133_BLOCKED_SETTINGS1"
STRINGS_MARKER = "// MARK: Jerkgram v1.2V BUILD133_BLOCKED_SETTINGS_STRINGS1"
HIDE_BLOCKED_MESSAGES_KEY = "jerkgram.Messages.HideBlockedMessages"
HIDE_BLOCKED_REACTIONS_KEY = "jerkgram.Messages.HideBlockedReactions"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 Settings] " + message)


def localized_settings_strings(language_code: str):
    if language_code.lower().split("-")[0] == "ru":
        return (
            "ЗАБЛОКИРОВАННЫЕ",
            "Скрывать сообщения заблокированных",
            "Скрывать реакции заблокированных",
        )
    return ("BLOCKED USERS", "Hide Blocked Messages", "Hide Blocked Reactions")


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
    raise RuntimeError("[Build133 Settings] unbalanced block: " + signature)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    require(count == 1, f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def array_close(text: str, array_open: int) -> int:
    require(array_open >= 0 and text[array_open] == "[", "invalid array start")
    depth = 0
    in_string = False
    escaped = False
    for index in range(array_open, len(text)):
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
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return index
    raise RuntimeError("[Build133 Settings] unbalanced entries array")


STRINGS_EXTENSION = r'''

// MARK: Jerkgram v1.2V BUILD133_BLOCKED_SETTINGS_STRINGS1
public extension JerkgramStrings {
    var blockedUsers: String {
        self.languageCode == "ru" ? "ЗАБЛОКИРОВАННЫЕ" : "BLOCKED USERS"
    }

    var hideBlockedMessages: String {
        self.languageCode == "ru"
            ? "Скрывать сообщения заблокированных"
            : "Hide Blocked Messages"
    }

    var hideBlockedReactions: String {
        self.languageCode == "ru"
            ? "Скрывать реакции заблокированных"
            : "Hide Blocked Reactions"
    }
}
'''


def patch_strings_text(text: str) -> str:
    if STRINGS_MARKER in text:
        require(text.count(STRINGS_MARKER) == 1, "strings marker is ambiguous")
        return text
    require("JerkgramStrings" in text, "JerkgramStrings foundation missing")
    require("languageCode" in text, "JerkgramStrings Telegram-language code missing")
    return text.rstrip() + STRINGS_EXTENSION + "\n"


def patch_settings_text(text: str) -> str:
    if MARKER in text:
        require(text.count(MARKER) == 1, "Settings marker is ambiguous")
        return text

    require("private enum GhostBaseKey" in text, "GhostBaseKey owner missing")
    require("private struct GhostBaseSettingsState" in text, "Settings state owner missing")
    require("private func ghostBaseSettingsEntries(" in text, "Settings entries owner missing")
    require("ItemListSwitchItem(" in text or "case let .toggle" in text, "native toggle renderer missing")

    # Stable keys: no key rename/migration churn in Build133.
    key_start, key_end = block_bounds(text, "private enum GhostBaseKey")
    key_block = text[key_start:key_end]
    require("hideBlockedMessages" not in key_block and "hideBlockedReactions" not in key_block, "blocked keys already exist without Build133 marker")
    brace = key_block.find("{")
    key_insert = (
        "\n    // Build133 blocked-user visibility settings.\n"
        f'    static let hideBlockedMessages = "{HIDE_BLOCKED_MESSAGES_KEY}"\n'
        f'    static let hideBlockedReactions = "{HIDE_BLOCKED_REACTIONS_KEY}"\n'
    )
    key_block = key_block[:brace + 1] + key_insert + key_block[brace + 1:]
    text = text[:key_start] + key_block + text[key_end:]

    # State fields.
    state_start, state_end = block_bounds(text, "private struct GhostBaseSettingsState")
    state = text[state_start:state_end]
    state_brace = state.find("{")
    state = state[:state_brace + 1] + (
        "\n    var hideBlockedMessages: Bool\n"
        "    var hideBlockedReactions: Bool\n"
    ) + state[state_brace + 1:]

    load_anchor = "return GhostBaseSettingsState("
    require(state.count(load_anchor) == 1, "Settings load constructor anchor mismatch")
    state = state.replace(
        load_anchor,
        load_anchor
        + "\n            hideBlockedMessages: ghostBaseBool(GhostBaseKey.hideBlockedMessages, defaultValue: true),"
        + "\n            hideBlockedReactions: ghostBaseBool(GhostBaseKey.hideBlockedReactions, defaultValue: true),",
        1,
    )

    save_sig = "func save()"
    save_rel_start, save_rel_end = block_bounds(state, save_sig)
    save = state[save_rel_start:save_rel_end]
    save_brace = save.find("{")
    save = save[:save_brace + 1] + (
        "\n        UserDefaults.standard.set(self.hideBlockedMessages, forKey: GhostBaseKey.hideBlockedMessages)"
        "\n        UserDefaults.standard.set(self.hideBlockedReactions, forKey: GhostBaseKey.hideBlockedReactions)\n"
    ) + save[save_brace + 1:]
    state = state[:save_rel_start] + save + state[save_rel_end:]
    text = text[:state_start] + state + text[state_end:]

    # Wire native updateBool state mutation; target only the key switch.
    switch_start, switch_end = block_bounds(text, "switch key {")
    switch = text[switch_start:switch_end]
    require(switch.count("default:") == 1, "updateBool default anchor mismatch")
    cases = '''        case GhostBaseKey.hideBlockedMessages:
            updated.hideBlockedMessages = value

        case GhostBaseKey.hideBlockedReactions:
            updated.hideBlockedReactions = value

'''
    switch = switch.replace("        default:\n", cases + "        default:\n", 1)
    text = text[:switch_start] + switch + text[switch_end:]

    # Add a distinct native section at the end of Messages. Section id is
    # derived from the existing page, so late Build133 does not renumber old rows.
    messages_start, messages_end = block_bounds(text, "if page == .messages {")
    messages = text[messages_start:messages_end]
    return_index = messages.find("return [")
    require(return_index >= 0, "Messages return array missing")
    open_index = messages.find("[", return_index)
    close_index = array_close(messages, open_index)
    array_text = messages[open_index:close_index + 1]
    section_ids = [int(value) for value in re.findall(r"\.(?:header|toggle|info|input|disclosure|valueDisclosure)\(\s*(\d+)", array_text)]
    require(section_ids, "Messages section ids missing")
    blocked_section = max(section_ids) + 1

    insertion = (
        f",\n            .header({blocked_section}, strings.blockedUsers),"
        f"\n            .toggle({blocked_section}, 1, GhostBaseKey.hideBlockedMessages, strings.hideBlockedMessages, state.hideBlockedMessages),"
        f"\n            .toggle({blocked_section}, 2, GhostBaseKey.hideBlockedReactions, strings.hideBlockedReactions, state.hideBlockedReactions)"
    )
    messages = messages[:close_index] + insertion + messages[close_index:]
    text = text[:messages_start] + messages + text[messages_end:]

    owner = "private func ghostBaseSettingsEntries("
    owner_index = text.find(owner)
    require(owner_index >= 0, "Settings entries owner disappeared")
    text = text[:owner_index] + MARKER + "\n" + text[owner_index:]

    require(text.count("strings.blockedUsers") == 1, "blocked section must be rendered once")
    require(text.count("GhostBaseKey.hideBlockedMessages, strings.hideBlockedMessages") == 1, "blocked messages row must be rendered once")
    require(text.count("GhostBaseKey.hideBlockedReactions, strings.hideBlockedReactions") == 1, "blocked reactions row must be rendered once")
    return text


def main() -> None:
    require(SETTINGS.is_file(), "Settings owner missing: " + str(SETTINGS))
    require(STRINGS.is_file(), "JerkgramStrings owner missing: " + str(STRINGS))

    settings = patch_settings_text(SETTINGS.read_text(encoding="utf-8"))
    strings = patch_strings_text(STRINGS.read_text(encoding="utf-8"))

    SETTINGS.write_text(settings, encoding="utf-8")
    STRINGS.write_text(strings, encoding="utf-8")
    print("[Build133 Settings] SOURCE PATCHED")


if __name__ == "__main__":
    main()
