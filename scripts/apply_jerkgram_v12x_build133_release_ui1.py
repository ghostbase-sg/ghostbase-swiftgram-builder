#!/usr/bin/env python3

from pathlib import Path
import os


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
SETTINGS = ROOT / "submodules/SettingsUI/Sources/GhostBase/GhostBaseSettingsController.swift"
STRINGS = ROOT / "submodules/TelegramPresentationData/Sources/JerkgramStrings.swift"

MARKER = "// MARK: Jerkgram v1.2X BUILD133_RELEASE_UI1"
IDENTITY_MARKER = "// MARK: Jerkgram v1.2X BUILD133_RELEASE_IDENTITY1"
DISPLAY_VERSION = "1.0.2"
TECHNICAL_VERSION = "1.0.2"
BUILD = "139"
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


ABOUT_OLD_VERSION = '            .aboutValue(1, 1, strings.jerkgramVersion, Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "—"),'
ABOUT_OLD_BUILD = '            .aboutValue(1, 2, strings.build, Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "—"),'
ABOUT_OLD_BASE = '            .aboutValue(1, 3, strings.telegramBase, "12.9.2"),'
ABOUT_NEW_VERSION = '            .aboutValue(1, 1, strings.jerkgramVersion, JerkgramReleaseIdentity.displayVersion),'
ABOUT_NEW_BUILD = '            .aboutValue(1, 2, strings.build, JerkgramReleaseIdentity.build),'
ABOUT_NEW_BASE = '            .aboutValue(1, 3, strings.telegramBase, JerkgramReleaseIdentity.telegramBase),'


def patch_settings_text(text: str) -> str:
    signature = "private func JerkgramSettingsStatusItem("

    if MARKER not in text:
        require("BUILD123_SETTINGS_SYSTEM1" in text, "Build123 Settings status prerequisite missing")
        old_owner = block_text(text, signature)
        require("ItemListDisclosureItem(" in old_owner, "expected legacy disclosure status owner missing")
        require("systemStyle: .glass" in old_owner, "expected legacy glass status owner missing")
        text = replace_block(text, signature, STATUS_OWNER)
    else:
        require(text.count(MARKER) == 1, "Settings release marker is ambiguous")

    # Keep Telegram's glass system style on every interactive row. Its native
    # mask uses a 26 pt radius; stripping it falls back to the nearly-square
    # 11 pt legacy mask seen in Build134. Status/footer text remains plain via
    # JerkgramSettingsStatusItem above and is not turned into a bubble.

    owner = block_text(text, signature)
    require("ItemListTextItem(" in owner and "text: .plain(text)" in owner, "native plain status owner not materialized")
    require("ItemListDisclosureItem(" not in owner, "legacy disclosure status owner survived")
    require("style: .blocks" not in owner, "legacy block/card status styling survived")

    about_start, about_end = block_bounds(text, "if page == .about {")
    about = text[about_start:about_end]
    if ABOUT_NEW_VERSION not in about:
        require(about.count(ABOUT_OLD_VERSION) == 1, "About Jerkgram Version owner changed")
        about = about.replace(ABOUT_OLD_VERSION, ABOUT_NEW_VERSION, 1)
    if ABOUT_NEW_BUILD not in about:
        require(about.count(ABOUT_OLD_BUILD) == 1, "About Build owner changed")
        about = about.replace(ABOUT_OLD_BUILD, ABOUT_NEW_BUILD, 1)
    if ABOUT_NEW_BASE not in about:
        require(about.count(ABOUT_OLD_BASE) == 1, "About Telegram Base owner changed")
        about = about.replace(ABOUT_OLD_BASE, ABOUT_NEW_BASE, 1)
    text = text[:about_start] + about + text[about_end:]

    for page in ("messages", "appearance", "about"):
        page_block = block_text(text, f"if page == .{page} {{")
        require(".info(" in page_block, f"{page} native info/footer row missing")

    about = block_text(text, "if page == .about {")
    require(ABOUT_NEW_VERSION.strip() in about, "About Jerkgram Version is not release-bound")
    require(ABOUT_NEW_BUILD.strip() in about, "About Build is not release-bound")
    require(ABOUT_NEW_BASE.strip() in about, "About Telegram Base is not release-bound")
    require('Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString")' not in about, "About still exposes Telegram plist version as Jerkgram Version")
    return text


def patch_strings_text(text: str) -> str:
    about_signature = "var build124AboutSummary: String {"
    if IDENTITY_MARKER in text:
        require(text.count(IDENTITY_MARKER) == 1, "release identity marker is ambiguous")
        about = block_text(text, about_signature)
        require("JerkgramReleaseIdentity.aboutText" in about, "legacy About summary is not release-bound")
        identity_start = text.index(IDENTITY_MARKER)
        _, identity_end = block_bounds(text, "public enum JerkgramReleaseIdentity")
        tail = text[identity_end:].strip("\n")
        updated = text[:identity_start].rstrip() + "\n\n" + IDENTITY_SOURCE.strip() + "\n"
        return updated if not tail else updated + "\n" + tail + "\n"

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
    text = text.rstrip() + "\n\n" + IDENTITY_SOURCE.strip() + "\n"

    about = block_text(text, about_signature)
    require("JerkgramReleaseIdentity.aboutText" in about, "legacy About summary release binding missing")
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
    print("[Build139 release UI] Jerkgram 1.0.2 / Build 139 / Telegram Base 12.9.2; 26pt glass interactive rows + plain status text")


if __name__ == "__main__":
    main()
