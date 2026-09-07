#!/usr/bin/env python3

from pathlib import Path
import os


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
APP_DELEGATE = ROOT / "TelegramUI/Sources/AppDelegate.swift"

BASE_MARKER = "// MARK: Jerkgram v1.2T BUILD130_TELEMETRY1"
MARKER = "// MARK: Jerkgram v1.2Y BUILD133_TELEMETRY_V2"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 telemetry v2] " + message)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    require(count == 1, f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


ACTIVE_OLD = "    func applicationDidBecomeActive() { queue.async { [weak self] in self?.submitIfNeeded() } }"
ACTIVE_NEW = '''    func applicationDidBecomeActive() {
        queue.async { [weak self] in
            guard let self else { return }
            guard JerkgramTelemetryPreferences.isEnabled else { return }
            self.recordOpen()
            self.submitIfNeeded()
        }
    }'''

KEY_ANCHOR = "    private let minimumInterval: TimeInterval = 4 * 60 * 60"
KEYS_NEW = '''    private let minimumInterval: TimeInterval = 4 * 60 * 60
    private let analyticsDayKey = "jerkgram.telemetry.analyticsDay.v2"
    private let openCountTodayKey = "jerkgram.telemetry.openCountToday.v2"'''

HELPER_ANCHOR = "    private func submitIfNeeded() {"
HELPERS = '''    private func analyticsDayString(_ date: Date) -> String {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "Europe/Moscow") ?? TimeZone(secondsFromGMT: 3 * 60 * 60)!
        let components = calendar.dateComponents([.year, .month, .day], from: date)
        return String(
            format: "%04d-%02d-%02d",
            components.year ?? 0,
            components.month ?? 0,
            components.day ?? 0
        )
    }

    private func recordOpen() {
        let defaults = UserDefaults.standard
        let analyticsDay = self.analyticsDayString(Date())
        let previousDay = defaults.string(forKey: self.analyticsDayKey)
        let previousCount = previousDay == analyticsDay ? defaults.integer(forKey: self.openCountTodayKey) : 0
        defaults.set(analyticsDay, forKey: self.analyticsDayKey)
        defaults.set(previousCount + 1, forKey: self.openCountTodayKey)
    }

    private func submitIfNeeded() {'''

SECRET_ANCHOR = "        let secret = localSecret(defaults: defaults)"
SECRET_NEW = '''        let secret = localSecret(defaults: defaults)
        let analyticsDay=analyticsDayString(now)
        let analyticsDayId=hmac(secret,"analytics-day:"+analyticsDay)
        let openCountToday=max(1,defaults.integer(forKey:openCountTodayKey))'''

VERSION_OLD = '        let version=Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? ""'
VERSION_NEW = "        let version=JerkgramReleaseIdentity.technicalVersion"
BUILD_OLD = '        let build=Bundle.main.object(forInfoDictionaryKey:"CFBundleVersion") as? String ?? ""'
BUILD_NEW = "        let build=JerkgramReleaseIdentity.build"

PAYLOAD_OLD = '        var payload:[String:Any]=["schema":1,"appVersion":version,"build":build,"iosVersion":os,"iosMajor":major,"deviceRegion":region,"installAgeDays":age,"dayId":dayId,"weekId":weekId,"monthId":monthId]'
PAYLOAD_NEW = '        var payload:[String:Any]=["schema":1,"appVersion":version,"build":build,"iosVersion":os,"iosMajor":major,"deviceRegion":region,"installAgeDays":age,"dayId":dayId,"weekId":weekId,"monthId":monthId,"analyticsDay":analyticsDay,"analyticsDayId":analyticsDayId,"openCountToday":openCountToday]'


def verify_transformed(text: str) -> None:
    require(text.count(MARKER) == 1, "telemetry v2 marker count != 1")
    require('https://jerkgram-telemetry.cronusk1809.workers.dev/v1/activity' in text, "telemetry endpoint changed")
    require('"schema":1' in text, "schema=1 disappeared")
    require('"dayId":dayId' in text and '"weekId":weekId' in text and '"monthId":monthId' in text, "legacy period IDs disappeared")
    require('payload["installReceiptId"]=receipt' in text, "installReceiptId disappeared")
    require("JerkgramReleaseIdentity.technicalVersion" in text, "technical Beta 2 identity is not used")
    require("JerkgramReleaseIdentity.build" in text, "Build133 identity is not used")
    require('forInfoDictionaryKey:"CFBundleShortVersionString"' not in text, "telemetry still reports Telegram 12.9.2 as appVersion")
    for field in ('"analyticsDay":analyticsDay', '"analyticsDayId":analyticsDayId', '"openCountToday":openCountToday'):
        require(field in text, "Telemetry v2 field missing: " + field)
    require('TimeZone(identifier: "Europe/Moscow")' in text, "Moscow analytics day missing")
    require(text.count("URLSession.shared.dataTask") == 1, "network owner count changed")
    require(text.count("private let endpoint = URL(") == 1, "endpoint owner count changed")
    require(text.count("guard JerkgramTelemetryPreferences.isEnabled else") >= 2, "OFF-before-network gates disappeared")


def patch_app_delegate_text(text: str) -> str:
    if MARKER in text:
        verify_transformed(text)
        return text

    require(BASE_MARKER in text, "Build130 telemetry baseline missing")
    text = replace_once(text, BASE_MARKER, BASE_MARKER + "\n" + MARKER, "telemetry marker")
    text = replace_once(text, KEY_ANCHOR, KEYS_NEW, "v2 storage keys")
    text = replace_once(text, ACTIVE_OLD, ACTIVE_NEW, "applicationDidBecomeActive owner")
    text = replace_once(text, HELPER_ANCHOR, HELPERS, "v2 helper insertion")
    text = replace_once(text, SECRET_ANCHOR, SECRET_NEW, "v2 payload derivation")
    text = replace_once(text, VERSION_OLD, VERSION_NEW, "technical app version")
    text = replace_once(text, BUILD_OLD, BUILD_NEW, "build identity")
    text = replace_once(text, PAYLOAD_OLD, PAYLOAD_NEW, "payload fields")
    verify_transformed(text)
    return text


def main() -> None:
    require(APP_DELEGATE.is_file(), "AppDelegate missing: " + str(APP_DELEGATE))
    APP_DELEGATE.write_text(patch_app_delegate_text(APP_DELEGATE.read_text(encoding="utf-8")), encoding="utf-8")
    print("[Build133 telemetry v2] SOURCE PATCHED")
    print("[Build133 telemetry v2] appVersion=1.0.2-beta.2 / build=133 / schema=1 / legacy IDs preserved / Moscow day counters additive")


if __name__ == "__main__":
    main()
