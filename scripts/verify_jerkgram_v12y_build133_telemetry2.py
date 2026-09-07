#!/usr/bin/env python3

from pathlib import Path
import os

import apply_jerkgram_v12y_build133_telemetry2 as patch


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
APP_DELEGATE = ROOT / "submodules/TelegramUI/Sources/AppDelegate.swift"
STRINGS = ROOT / "submodules/TelegramPresentationData/Sources/JerkgramStrings.swift"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 telemetry v2 verify] " + message)


def verify_release_identity(text: str) -> None:
    for token in (
        'displayVersion = "1.0.2 Beta 2"',
        'technicalVersion = "1.0.2-beta.2"',
        'build = "133"',
        'telegramBase = "12.9.2"',
    ):
        require(token in text, "shared release identity token missing: " + token)


def verify_telemetry_owner(text: str) -> None:
    patch.verify_transformed(text)
    require(text.count("JerkgramReleaseIdentity.technicalVersion") == 1, "appVersion release identity owner count")
    require(text.count("JerkgramReleaseIdentity.build") == 1, "build release identity owner count")
    require(text.index("guard JerkgramTelemetryPreferences.isEnabled else") < text.index("URLSession.shared.dataTask"), "OFF gate must precede network task")
    require('"analyticsDay":analyticsDay' in text, "analyticsDay missing")
    require('"analyticsDayId":analyticsDayId' in text, "analyticsDayId missing")
    require('"openCountToday":openCountToday' in text, "openCountToday missing")
    require('payload["installReceiptId"]=receipt' in text, "installReceiptId missing")


def main() -> None:
    require(APP_DELEGATE.is_file(), "AppDelegate missing: " + str(APP_DELEGATE))
    require(STRINGS.is_file(), "JerkgramStrings missing: " + str(STRINGS))
    verify_release_identity(STRINGS.read_text(encoding="utf-8"))
    verify_telemetry_owner(APP_DELEGATE.read_text(encoding="utf-8"))
    print("[Build133 telemetry v2 verify] PREFLIGHT GREEN")
    print("[Build133 telemetry v2 verify] 1.0.2-beta.2 / build 133 / legacy privacy IDs + Moscow counters preserved")


if __name__ == "__main__":
    main()
