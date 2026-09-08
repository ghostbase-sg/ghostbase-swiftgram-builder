#!/usr/bin/env python3

from pathlib import Path
import os

import apply_jerkgram_v12za_build134_gift_localization1 as patch


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
GIFT_OPTIONS = ROOT / "submodules/TelegramUI/Components/Gifts/GiftOptionsScreen/Sources/GiftOptionsScreen.swift"


def main() -> None:
    patch.require(GIFT_OPTIONS.is_file(), "missing GiftOptionsScreen owner")
    text = GIFT_OPTIONS.read_text(encoding="utf-8")
    patch.require(text.count(patch.MARKER) == 1, "localization marker count")
    patch.require('strings.baseLanguageCode == "ru" ? "Сезонные" : "Seasonal"' in text, "localized seasonal tab missing")
    patch.require('environment.strings.baseLanguageCode == "ru" ? "Сезонный" : "Seasonal"' in text, "localized seasonal ribbon missing")
    patch.require('title: "Сезонные"' not in text, "hard-coded Russian seasonal tab survived")
    patch.require('text: "Сезонный"' not in text, "hard-coded Russian seasonal ribbon survived")
    print("[Build134 gift localization verifier] GREEN")


if __name__ == "__main__":
    main()
