#!/usr/bin/env python3

from pathlib import Path
import os

import apply_jerkgram_v12x_build133_release_ui1 as patch


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
SETTINGS = ROOT / "submodules/SettingsUI/Sources/GhostBase/GhostBaseSettingsController.swift"
STRINGS = ROOT / "submodules/TelegramPresentationData/Sources/JerkgramStrings.swift"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 release UI verify] " + message)


def verify_settings_owner(text: str) -> None:
    require(text.count(patch.MARKER) == 1, "release UI marker count != 1")
    owner = patch.block_text(text, "private func JerkgramSettingsStatusItem(")
    require("ItemListTextItem(" in owner, "status/info is not Telegram native text")
    require("text: .plain(text)" in owner, "status/info is not plain text")
    require("ItemListDisclosureItem(" not in owner, "status/info still uses disclosure bubble")
    require("style: .blocks" not in owner, "status/info still uses block/card styling")
    require("systemStyle: .glass" not in text, "Jerkgram Settings still contains glass/bubble rows")

    for page in ("messages", "appearance", "about"):
        page_block = patch.block_text(text, f"if page == .{page} {{")
        require(".info(" in page_block, f"{page} footer/info row missing")

    about = patch.block_text(text, "if page == .about {")
    require("strings.jerkgramVersion, JerkgramReleaseIdentity.displayVersion" in about, "Jerkgram Version does not use release identity")
    require("strings.build, JerkgramReleaseIdentity.build" in about, "Build row does not use release identity")
    require("strings.telegramBase, JerkgramReleaseIdentity.telegramBase" in about, "Telegram Base row does not use release identity")
    require("CFBundleShortVersionString" not in about, "Jerkgram Version still leaks Telegram CFBundleShortVersionString")
    require('Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion")' not in about, "Build row still reads plist directly")


def verify_release_strings(text: str) -> None:
    require(text.count(patch.IDENTITY_MARKER) == 1, "release identity marker count != 1")
    summary = patch.block_text(text, "var build124AboutSummary: String {")
    require("JerkgramReleaseIdentity.aboutText" in summary, "legacy About summary is not bound to JerkgramReleaseIdentity")
    require("Build 124 Canary" not in summary, "stale Build124 About summary survived")

    for token in (
        'displayVersion = "1.0.2 Beta 2"',
        'technicalVersion = "1.0.2-beta.2"',
        'build = "133"',
        'telegramBase = "12.9.2"',
        '"Jerkgram Version \\(displayVersion)\\nBuild \\(build)\\nTelegram Base \\(telegramBase)"',
    ):
        require(token in text, "release identity token missing: " + token)


def main() -> None:
    require(SETTINGS.is_file(), "Settings owner missing: " + str(SETTINGS))
    require(STRINGS.is_file(), "JerkgramStrings owner missing: " + str(STRINGS))
    verify_settings_owner(SETTINGS.read_text(encoding="utf-8"))
    verify_release_strings(STRINGS.read_text(encoding="utf-8"))
    print("[Build133 release UI verify] PREFLIGHT GREEN")
    print("[Build133 release UI verify] flat native Settings + 1.0.2 Beta 2 / Build 133 / Telegram Base 12.9.2")


if __name__ == "__main__":
    main()
