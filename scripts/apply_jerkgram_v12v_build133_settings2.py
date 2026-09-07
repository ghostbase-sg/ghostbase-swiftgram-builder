#!/usr/bin/env python3

import re

import apply_jerkgram_v12v_build133_settings1 as base


STATE_SIGNATURE = "struct GhostBaseSettingsState: Equatable"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 Settings2] " + message)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    require(count == 1, f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_blocked_runtime_commit(text: str) -> str:
    sync_anchor = '''        GhostBaseKey.oneTimeSave,
    ]'''
    sync_replacement = '''        GhostBaseKey.oneTimeSave,
        GhostBaseKey.hideBlockedMessages,
        GhostBaseKey.hideBlockedReactions,
    ]'''
    text = replace_once(text, sync_anchor, sync_replacement, "blocked synchronous runtime keys")

    deferred_anchor = "\n    let deferredChanges = changes.filter {\n"
    notify = '''
    if changes[GhostBaseKey.hideBlockedMessages] != nil
        || changes[GhostBaseKey.hideBlockedReactions] != nil {
        JerkgramBlockedReactionPolicy.notifySettingsChanged()
    }
'''
    text = replace_once(text, deferred_anchor, notify + deferred_anchor, "blocked runtime refresh notification")
    return text


def patch_settings_text(text: str) -> str:
    if base.MARKER in text:
        require(text.count(base.MARKER) == 1, "Settings marker is ambiguous")
        return text

    # Build123/124 owns Settings persistence by account. Build133 must extend
    # that owner rather than creating a second UserDefaults/save path.
    require(text.count("private enum GhostBaseKey") == 1, "GhostBaseKey owner missing or ambiguous")
    require(text.count(STATE_SIGNATURE) == 1, "account-scoped Settings state owner missing or ambiguous")
    require(text.count("private func jerkgramStateValues(_ state: GhostBaseSettingsState)") == 1, "account-scoped state map owner missing or ambiguous")
    require(text.count("private func jerkgramPersistChangedSettings(") == 1, "account-scoped persistence owner missing or ambiguous")
    require(text.count("private func ghostBaseSettingsEntries(") == 1, "Settings entries owner missing or ambiguous")
    require("jerkgramScopedSettingsKey(accountPeerId: Int64, key: String)" in text, "scoped settings key owner missing")
    require('return "jerkgram.account.\\(accountPeerId).setting.\\(key)"' in text, "scoped settings key format changed")

    # Stable semantic storage keys. These literals intentionally match the
    # v12t runtime policy; no rename or migration is introduced in Build133.
    key_anchor = '    static let showEditHistory = "jerkgram.Messages.ShowEditHistory"\n'
    key_insert = (
        key_anchor
        + f'    static let hideBlockedMessages = "{base.HIDE_BLOCKED_MESSAGES_KEY}"\n'
        + f'    static let hideBlockedReactions = "{base.HIDE_BLOCKED_REACTIONS_KEY}"\n'
    )
    require("static let hideBlockedMessages" not in text and "static let hideBlockedReactions" not in text, "blocked keys already exist without Build133 marker")
    text = replace_once(text, key_anchor, key_insert, "blocked storage keys")

    # Extend the canonical account-scoped state and its persistence projection.
    state_field_anchor = "    var showEditHistory: Bool\n"
    text = replace_once(
        text,
        state_field_anchor,
        state_field_anchor + "    var hideBlockedMessages: Bool\n    var hideBlockedReactions: Bool\n",
        "blocked state fields",
    )

    state_map_anchor = "        GhostBaseKey.showEditHistory: .bool(state.showEditHistory),\n"
    text = replace_once(
        text,
        state_map_anchor,
        state_map_anchor
        + "        GhostBaseKey.hideBlockedMessages: .bool(state.hideBlockedMessages),\n"
        + "        GhostBaseKey.hideBlockedReactions: .bool(state.hideBlockedReactions),\n",
        "account-scoped state map",
    )

    load_anchor = (
        "            showEditHistory: jerkgramScopedBool(accountPeerId: accountPeerId, "
        "key: GhostBaseKey.showEditHistory, defaultValue: true),\n"
    )
    text = replace_once(
        text,
        load_anchor,
        load_anchor
        + "            hideBlockedMessages: jerkgramScopedBool(accountPeerId: accountPeerId, key: GhostBaseKey.hideBlockedMessages, defaultValue: true),\n"
        + "            hideBlockedReactions: jerkgramScopedBool(accountPeerId: accountPeerId, key: GhostBaseKey.hideBlockedReactions, defaultValue: true),\n",
        "account-scoped state load",
    )

    # Update only the canonical updateBool switch. jerkgramPersistChangedSettings
    # observes the state-map delta and writes scoped + compatibility projections.
    update_anchor = "            case GhostBaseKey.showEditHistory:\n                updated.showEditHistory = value\n"
    update_insert = (
        update_anchor
        + "            case GhostBaseKey.hideBlockedMessages:\n"
        + "                updated.hideBlockedMessages = value\n"
        + "            case GhostBaseKey.hideBlockedReactions:\n"
        + "                updated.hideBlockedReactions = value\n"
    )
    text = replace_once(text, update_anchor, update_insert, "updateBool blocked cases")

    # The visibility switches are runtime-critical: commit them before the
    # refresh signal so an already-open chat reads the new value immediately.
    text = patch_blocked_runtime_commit(text)

    # Add one independent native section at the end of Messages. Existing
    # sections and row ids are left untouched; .toggle already renders through
    # Telegram's ItemListSwitchItem owner.
    messages_start, messages_end = base.block_bounds(text, "if page == .messages {")
    messages = text[messages_start:messages_end]
    return_index = messages.find("return [")
    require(return_index >= 0, "Messages return array missing")
    open_index = messages.find("[", return_index)
    close_index = base.array_close(messages, open_index)
    array_text = messages[open_index:close_index + 1]
    section_ids = [
        int(value)
        for value in re.findall(
            r"\.(?:header|toggle|info|input|disclosure|valueDisclosure|selector|stylePreview)\(\s*(\d+)",
            array_text,
        )
    ]
    require(section_ids, "Messages section ids missing")
    blocked_section = max(section_ids) + 1

    # The canonical Messages array may already use a trailing comma on its last
    # item. Emit a separator only when one is actually needed. The previous
    # Build133 patch always prepended a comma and could materialize `),\n,\n.header`,
    # which is invalid Swift and caused SettingsUI to fail after a long Bazel run.
    existing_array_body = messages[open_index + 1:close_index].rstrip()
    separator = "" if existing_array_body.endswith(",") else ","
    insertion = (
        f"{separator}\n            .header({blocked_section}, strings.blockedUsers),"
        f"\n            .toggle({blocked_section}, 1, GhostBaseKey.hideBlockedMessages, strings.hideBlockedMessages, state.hideBlockedMessages),"
        f"\n            .toggle({blocked_section}, 2, GhostBaseKey.hideBlockedReactions, strings.hideBlockedReactions, state.hideBlockedReactions)"
    )
    messages = messages[:close_index] + insertion + messages[close_index:]
    require(
        re.search(r"\n\s*,\s*\n\s*\.header\(\d+,\s*strings\.blockedUsers\)", messages) is None,
        "standalone comma before blocked section",
    )
    text = text[:messages_start] + messages + text[messages_end:]

    owner = "private func ghostBaseSettingsEntries("
    owner_index = text.find(owner)
    require(owner_index >= 0, "Settings entries owner disappeared")
    text = text[:owner_index] + base.MARKER + "\n" + text[owner_index:]

    # Final fail-closed structural proof for this overlay.
    require(text.count(base.MARKER) == 1, "Settings marker count != 1")
    require(text.count("GhostBaseKey.hideBlockedMessages: .bool(state.hideBlockedMessages)") == 1, "blocked-message state map count != 1")
    require(text.count("GhostBaseKey.hideBlockedReactions: .bool(state.hideBlockedReactions)") == 1, "blocked-reaction state map count != 1")
    require(text.count("jerkgramScopedBool(accountPeerId: accountPeerId, key: GhostBaseKey.hideBlockedMessages") == 1, "blocked-message scoped load count != 1")
    require(text.count("jerkgramScopedBool(accountPeerId: accountPeerId, key: GhostBaseKey.hideBlockedReactions") == 1, "blocked-reaction scoped load count != 1")
    require(text.count("JerkgramBlockedReactionPolicy.notifySettingsChanged()") == 1, "blocked runtime refresh notification count != 1")
    require(text.count("strings.blockedUsers") == 1, "blocked section must render once")
    require(text.count("GhostBaseKey.hideBlockedMessages, strings.hideBlockedMessages") == 1, "blocked-message native row must render once")
    require(text.count("GhostBaseKey.hideBlockedReactions, strings.hideBlockedReactions") == 1, "blocked-reaction native row must render once")
    return text


def main() -> None:
    require(base.SETTINGS.is_file(), "Settings owner missing: " + str(base.SETTINGS))
    require(base.STRINGS.is_file(), "JerkgramStrings owner missing: " + str(base.STRINGS))

    settings = patch_settings_text(base.SETTINGS.read_text(encoding="utf-8"))
    strings = base.patch_strings_text(base.STRINGS.read_text(encoding="utf-8"))
    base.SETTINGS.write_text(settings, encoding="utf-8")
    base.STRINGS.write_text(strings, encoding="utf-8")
    print("[Build133 Settings2] SOURCE PATCHED: account-scoped owner preserved")


if __name__ == "__main__":
    main()
