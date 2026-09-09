#!/usr/bin/env python3

from pathlib import Path
import os

import apply_jerkgram_v12y_build133_telemetry2 as patch
import apply_jerkgram_v12x_build133_release_ui1 as release


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
APP_DELEGATE = ROOT / "submodules/TelegramUI/Sources/AppDelegate.swift"
STRINGS = ROOT / "submodules/TelegramPresentationData/Sources/JerkgramStrings.swift"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 telemetry v2 verify] " + message)


def verify_release_identity(text: str) -> None:
    for token in (
        f'displayVersion = "{release.DISPLAY_VERSION}"',
        f'technicalVersion = "{release.TECHNICAL_VERSION}"',
        f'build = "{release.BUILD}"',
        f'telegramBase = "{release.TELEGRAM_BASE}"',
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
    require('"deviceModel":model' in text and "uname(&info)" in text, "deviceModel v2.1 field missing")
    require('"event":"app_active"' in text and '"ts":Int(now.timeIntervalSince1970)' in text, "event/timestamp v2.1 fields missing")
    require("applicationDidEnterBackground()" in text, "background lifecycle state missing")
    require("defaults.set(now,forKey:lastAttemptAtKey)" in text, "attempt throttling missing")
    require('payload["installReceiptId"]=receipt' in text, "installReceiptId missing")


def main() -> None:
    require(APP_DELEGATE.is_file(), "AppDelegate missing: " + str(APP_DELEGATE))
    require(STRINGS.is_file(), "JerkgramStrings missing: " + str(STRINGS))
    verify_release_identity(STRINGS.read_text(encoding="utf-8"))
    verify_telemetry_owner(APP_DELEGATE.read_text(encoding="utf-8"))
    print(f"[Build{release.BUILD} telemetry v2.1 verify] PREFLIGHT GREEN")
    print(f"[Build{release.BUILD} telemetry v2.1 verify] {release.TECHNICAL_VERSION} / build {release.BUILD} / full legacy payload + Moscow counters preserved")


if __name__ == "__main__":
    main()
