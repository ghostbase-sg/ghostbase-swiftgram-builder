#!/usr/bin/env python3

from pathlib import Path
import os

import apply_jerkgram_v12z_build134_context_localization1 as patch


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
STRINGS = ROOT / "submodules/TelegramPresentationData/Sources/JerkgramStrings.swift"
MENU = ROOT / "submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build134 context localization verify] " + message)


def verify_strings_owner(text: str) -> None:
    require(text.count(patch.STRINGS_MARKER) == 1, "strings marker count")
    localized = text[text.index(patch.STRINGS_MARKER):]
    for token in (
        "var messageHistory: String",
        'self.languageCode == "ru" ? "История" : "History"',
        "var forwardWithoutAuthor: String",
        'self.languageCode == "ru" ? "Переслать без автора" : "Forward without author"',
    ):
        require(token in localized, "localized string missing: " + token)
    require("Locale.current" not in localized, "context strings use device locale")


def verify_menu_owner(text: str) -> None:
    require(text.count(patch.MENU_MARKER) == 1, "menu marker count")
    require(text.count("text: chatPresentationInterfaceState.strings.jerkgram.messageHistory") == 1, "localized history context row count")
    require(text.count("controller.title = chatPresentationInterfaceState.strings.jerkgram.messageHistory") == 1, "localized history title count")
    require(text.count("text: chatPresentationInterfaceState.strings.jerkgram.forwardWithoutAuthor") == 1, "localized forward-without-author row count")
    for stale in (
        'ContextMenuActionItem(text: "История"',
        'controller.title = "История"',
        'text: "Переслать без автора"',
    ):
        require(stale not in text, "hardcoded UI owner survived: " + stale)


def main() -> None:
    require(STRINGS.is_file(), "strings source missing: " + str(STRINGS))
    require(MENU.is_file(), "context-menu source missing: " + str(MENU))
    verify_strings_owner(STRINGS.read_text(encoding="utf-8"))
    verify_menu_owner(MENU.read_text(encoding="utf-8"))
    print("[Build134 context localization verify] PREFLIGHT GREEN")
    print("[Build134 context localization verify] RU/EN follow Telegram selected language")


if __name__ == "__main__":
    main()
