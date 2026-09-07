#!/usr/bin/env python3

from pathlib import Path
import os


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
SETTINGS = ROOT / "submodules/SettingsUI/Sources/GhostBase/GhostBaseSettingsController.swift"
STRINGS = ROOT / "submodules/TelegramPresentationData/Sources/JerkgramStrings.swift"

MARKER = "// MARK: Jerkgram v1.2X BUILD133_RELEASE_UI1"
IDENTITY_MARKER = "// MARK: Jerkgram v1.2X BUILD133_RELEASE_IDENTITY1"
DISPLAY_VERSION = "1.0.2 Beta 1"
TECHNICAL_VERSION = "1.0.2-beta.1"
BUILD = "133"
TELEGRAM_BASE = "12.9.2"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 release UI] " + message)


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
    raise RuntimeError("[Build133 release UI] unbalanced block: " + signature)


def block_text(text: str, signature: str) -> str:
    start, end = block_bounds(text, signature)
    return text[start:end]


def replace_block(text: str, signature: str, replacement: str) -> str:
    start, end = block_bounds(text, signature)
    return text[:start] + replacement + text[end:]


STATUS_OWNER = '''// MARK: Jerkgram v1.2X BUILD133_RELEASE_UI1
private func JerkgramSettingsStatusItem(
    presentationData: ItemListPresentationData,
    text: String,
    sectionId: ItemListSectionId
) -> ListViewItem {
    // A footer/status is text, not a tappable card. Keep Telegram's native
    // ItemListTextItem owner so About / Appearance / Messages do not render
    // glass pills or disclosure-shaped fake controls.
    return ItemListTextItem(
        presentationData: presentationData,
        text: .plain(text),
        sectionId: sectionId
    )
}'''


IDENTITY_SOURCE = f'''

// MARK: Jerkgram v1.2X BUILD133_RELEASE_IDENTITY1
public enum JerkgramReleaseIdentity {{
    public static let displayVersion = "{DISPLAY_VERSION}"
    public static let technicalVersion = "{TECHNICAL_VERSION}"
    public static let build = "{BUILD}"
    public static let telegramBase = "{TELEGRAM_BASE}"

    public static var aboutText: String {{
        return "Jerkgram Version \\(displayVersion)\\nBuild \\(build)\\nTelegram Base \\(telegramBase)"
    }}
}}
'''


def patch_settings_text(text: str) -> str:
    signature = "private func JerkgramSettingsStatusItem("
    if MARKER in text:
        require(text.count(MARKER) == 1, "Settings release marker is ambiguous")
        owner = block_text(text, signature)
        require("ItemListTextItem(" in owner, "native status text owner missing")
        require("text: .plain(text)" in owner, "plain status text missing")
        require("ItemListDisclosureItem(" not in owner, "glass/disclosure status owner survived")
        require("systemStyle: .glass" not in owner, "glass status owner survived")
        return text

    require("BUILD123_SETTINGS_SYSTEM1" in text, "Build123 Settings status prerequisite missing")
    old_owner = block_text(text, signature)
    require("ItemListDisclosureItem(" in old_owner, "expected legacy disclosure status owner missing")
    require("systemStyle: .glass" in old_owner, "expected legacy glass status owner missing")

    text = replace_block(text, signature, STATUS_OWNER)
    owner = block_text(text, signature)
    require("ItemListTextItem(" in owner and "text: .plain(text)" in owner, "native plain status owner not materialized")
    require("ItemListDisclosureItem(" not in owner and "systemStyle: .glass" not in owner, "legacy bubble survived in status owner")

    # Do not rebuild page arrays. Existing .info rows in About / Appearance /
    # Messages keep their stable ids and now render through the native text owner.
    for page in ("messages", "appearance", "about"):
        page_block = block_text(text, f"if page == .{page} {{")
        require(".info(" in page_block, f"{page} native info/footer row missing")
    return text


def patch_strings_text(text: str) -> str:
    about_signature = "var build124AboutSummary: String {"
    if IDENTITY_MARKER in text:
        require(text.count(IDENTITY_MARKER) == 1, "release identity marker is ambiguous")
        about = block_text(text, about_signature)
        require("JerkgramReleaseIdentity.aboutText" in about, "About is not bound to release identity")
        return text

    require("BUILD124_SETTINGS_REDESIGN_STRINGS1" in text, "Build124 Settings strings prerequisite missing")
    about = block_text(text, about_signature)
    require("Build 124 Canary" in about, "stale About summary anchor changed unexpectedly")
    text = replace_block(
        text,
        about_signature,
        '''var build124AboutSummary: String {
        return JerkgramReleaseIdentity.aboutText
    }''',
    )
    text = text.rstrip() + IDENTITY_SOURCE + "\n"

    about = block_text(text, about_signature)
    require("JerkgramReleaseIdentity.aboutText" in about, "About release binding missing")
    for token in (
        f'displayVersion = "{DISPLAY_VERSION}"',
        f'technicalVersion = "{TECHNICAL_VERSION}"',
        f'build = "{BUILD}"',
        f'telegramBase = "{TELEGRAM_BASE}"',
    ):
        require(token in text, "release identity token missing: " + token)
    return text


def main() -> None:
    require(SETTINGS.is_file(), "Settings owner missing: " + str(SETTINGS))
    require(STRINGS.is_file(), "JerkgramStrings owner missing: " + str(STRINGS))

    SETTINGS.write_text(patch_settings_text(SETTINGS.read_text(encoding="utf-8")), encoding="utf-8")
    STRINGS.write_text(patch_strings_text(STRINGS.read_text(encoding="utf-8")), encoding="utf-8")
    print("[Build133 release UI] SOURCE PATCHED")
    print("[Build133 release UI] Jerkgram 1.0.2 Beta 1 / Build 133 / Telegram Base 12.9.2; native plain info rows")


if __name__ == "__main__":
    main()
