#!/usr/bin/env python3

from pathlib import Path
import os


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
GIFT_OPTIONS = ROOT / "submodules/TelegramUI/Components/Gifts/GiftOptionsScreen/Sources/GiftOptionsScreen.swift"
MARKER = "// MARK: Jerkgram v1.2ZA BUILD134_SEASONAL_GIFT_LOCALIZATION1"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build134 gift localization] " + message)


def seasonal_labels(language_code: str):
    if language_code.lower().split("-")[0] == "ru":
        return "Сезонные", "Сезонный"
    return "Seasonal", "Seasonal"


def patch_source(text: str) -> str:
    if MARKER in text:
        require(text.count(MARKER) == 1, "localization marker is ambiguous")
        return text

    tab = 'title: "Сезонные"'
    ribbon = 'text: "Сезонный"'
    require(text.count(tab) == 1, f"seasonal tab owner: expected one, found {text.count(tab)}")
    require(text.count(ribbon) == 1, f"seasonal ribbon owner: expected one, found {text.count(ribbon)}")
    text = text.replace(
        tab,
        '// MARK: Jerkgram v1.2ZA BUILD134_SEASONAL_GIFT_LOCALIZATION1\n'
        '                            title: strings.baseLanguageCode == "ru" ? "Сезонные" : "Seasonal"',
        1,
    )
    text = text.replace(
        ribbon,
        'text: environment.strings.baseLanguageCode == "ru" ? "Сезонный" : "Seasonal"',
        1,
    )
    return text


def main() -> None:
    require(GIFT_OPTIONS.is_file(), "missing GiftOptionsScreen owner: " + str(GIFT_OPTIONS))
    GIFT_OPTIONS.write_text(patch_source(GIFT_OPTIONS.read_text(encoding="utf-8")), encoding="utf-8")
    print("[Build134 gift localization] Telegram language -> seasonal tab and gift ribbon")


if __name__ == "__main__":
    main()
