#!/usr/bin/env python3

from pathlib import Path
import os


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
STRINGS = ROOT / "submodules/TelegramPresentationData/Sources/JerkgramStrings.swift"
MENU = ROOT / "submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift"

STRINGS_MARKER = "// MARK: Jerkgram v1.2Z BUILD134_CONTEXT_LOCALIZATION1"
MENU_MARKER = "// MARK: Jerkgram v1.2Z BUILD134_CONTEXT_MENU_LOCALIZATION1"

STRINGS_EXTENSION = r'''

// MARK: Jerkgram v1.2Z BUILD134_CONTEXT_LOCALIZATION1
// These labels follow Telegram's selected interface language through
// PresentationStrings.baseLanguageCode. English remains the fallback.
public extension JerkgramStrings {
    var messageHistory: String {
        return self.languageCode == "ru" ? "История" : "History"
    }

    var forwardWithoutAuthor: String {
        return self.languageCode == "ru" ? "Переслать без автора" : "Forward without author"
    }
}
'''


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build134 context localization] " + message)


def patch_strings_text(text: str) -> str:
    if STRINGS_MARKER in text:
        return text
    require("public struct JerkgramStrings" in text, "JerkgramStrings owner missing")
    return text.rstrip() + "\n" + STRINGS_EXTENSION


def patch_menu_text(text: str) -> str:
    if MENU_MARKER in text:
        return text

    history_row = 'ContextMenuActionItem(text: "История"'
    history_title = 'controller.title = "История"'
    forward_row = 'text: "Переслать без автора"'
    require(text.count(history_row) == 1, "history context-row owner count")
    require(text.count(history_title) == 1, "history title owner count")
    require(text.count(forward_row) == 1, "forward-without-author owner count")

    text = text.replace(history_row, "ContextMenuActionItem(text: chatPresentationInterfaceState.strings.jerkgram.messageHistory", 1)
    text = text.replace(history_title, "controller.title = chatPresentationInterfaceState.strings.jerkgram.messageHistory", 1)
    text = text.replace(forward_row, "text: chatPresentationInterfaceState.strings.jerkgram.forwardWithoutAuthor", 1)

    marker_anchor = "if ghostBaseShowEditHistory && !ghostBaseEditHistoryVersions.isEmpty {"
    require(text.count(marker_anchor) == 1, "edit-history visibility owner count")
    return text.replace(marker_anchor, MENU_MARKER + "\n        " + marker_anchor, 1)


def main() -> None:
    require(STRINGS.is_file(), "strings source missing: " + str(STRINGS))
    require(MENU.is_file(), "context-menu source missing: " + str(MENU))
    STRINGS.write_text(patch_strings_text(STRINGS.read_text(encoding="utf-8")), encoding="utf-8")
    MENU.write_text(patch_menu_text(MENU.read_text(encoding="utf-8")), encoding="utf-8")
    print("[Build134 context localization] GREEN")
    print("[Build134 context localization] Telegram language -> History / Forward without author / history title")


if __name__ == "__main__":
    main()
