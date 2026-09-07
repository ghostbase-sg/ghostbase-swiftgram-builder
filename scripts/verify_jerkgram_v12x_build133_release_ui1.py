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
    require("systemStyle: .glass" not in owner, "status/info still uses glass bubble")
    require("style: .blocks" not in owner, "status/info still uses block/card styling")

    for page in ("messages", "appearance", "about"):
        page_block = patch.block_text(text, f"if page == .{page} {{")
        require(".info(" in page_block, f"{page} footer/info row missing")


def verify_release_strings(text: str) -> None:
    require(text.count(patch.IDENTITY_MARKER) == 1, "release identity marker count != 1")
    about = patch.block_text(text, "var build124AboutSummary: String {")
    require("JerkgramReleaseIdentity.aboutText" in about, "About is not bound to JerkgramReleaseIdentity")
    require("Build 124 Canary" not in about, "stale Build124 About summary survived")

    for token in (
        'displayVersion = "1.0.2 Beta 1"',
        'technicalVersion = "1.0.2-beta.1"',
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
    print("[Build133 release UI verify] native .info + 1.0.2 Beta 1 / Build 133 / Telegram Base 12.9.2")


if __name__ == "__main__":
    main()
