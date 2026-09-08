#!/usr/bin/env python3

from pathlib import Path
import os


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
APP_DELEGATE = ROOT / "submodules/TelegramUI/Sources/AppDelegate.swift"

BASE_MARKER = "// MARK: Jerkgram v1.2T BUILD130_TELEMETRY1"
MARKER = "// MARK: Jerkgram v1.2Y BUILD133_TELEMETRY_V2"
ADDENDUM_MARKER = "// MARK: Jerkgram v1.2Y BUILD133_TELEMETRY_V2_1"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 telemetry v2] " + message)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    require(count == 1, f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def ensure_darwin_import(text: str) -> str:
    if "import Darwin" in text:
        return text
    import_anchor = "import Foundation"
    if import_anchor not in text:
        return text
    return replace_once(text, import_anchor, import_anchor + "\nimport Darwin", "Darwin import")


def patch_background_lifecycle(text: str) -> str:
    call = "        JerkgramTelemetry.shared.applicationDidEnterBackground()\n"
    if call in text:
        require(text.count(call) == 1, "background telemetry lifecycle call duplicated")
        return text
    signature = "    func applicationDidEnterBackground(_ application: UIApplication) {\n"
    require(signature in text, "AppDelegate background lifecycle owner missing")
    return replace_once(text, signature, signature + call, "background lifecycle call")


ACTIVE_OLD = "    func applicationDidBecomeActive() { queue.async { [weak self] in self?.submitIfNeeded() } }"
ACTIVE_NEW = '''    func applicationDidBecomeActive() {
        let shouldCountOpen = !self.hasSeenActive || self.enteredBackground
        self.hasSeenActive = true
        self.enteredBackground = false
        guard JerkgramTelemetryPreferences.isEnabled else { return }
        guard shouldCountOpen else { return }
        queue.async { [weak self] in
            guard let self else { return }
            guard JerkgramTelemetryPreferences.isEnabled else { return }
            self.recordOpen()
            self.submitIfNeeded()
        }
    }
    func applicationDidEnterBackground() {
        self.enteredBackground = true
    }'''

KEY_ANCHOR = "    private let minimumInterval: TimeInterval = 4 * 60 * 60"
KEYS_NEW = '''    private let minimumInterval: TimeInterval = 4 * 60 * 60
    private let lastAttemptAtKey = "jerkgram.telemetry.lastAttempt.v2"
    private let analyticsDayKey = "jerkgram.telemetry.opens.day"
    private let openCountTodayKey = "jerkgram.telemetry.opens.count"
    private let maximumOpenCount = 100000
    private var hasSeenActive = false
    private var enteredBackground = false'''

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
        defaults.set(min(self.maximumOpenCount, max(0, previousCount) + 1), forKey: self.openCountTodayKey)
    }

    private func submitIfNeeded() {'''

SECRET_ANCHOR = "        let secret = localSecret(defaults: defaults)"
SECRET_NEW = '''        let secret = localSecret(defaults: defaults)
        let analyticsDay=analyticsDayString(now)
        let analyticsDayId=hmac(secret,"jerkgram-msk-day-v1:"+analyticsDay)
        let openCountToday=max(1,defaults.integer(forKey:openCountTodayKey))'''

INTERVAL_OLD = "        if let last = defaults.object(forKey: lastSuccessKey) as? Date, now.timeIntervalSince(last) < minimumInterval { return }"
INTERVAL_NEW = "        if let last = defaults.object(forKey: lastAttemptAtKey) as? Date, now.timeIntervalSince(last) < minimumInterval { return }"

VERSION_OLD = '        let version=Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? ""'
VERSION_NEW = "        let version=JerkgramReleaseIdentity.technicalVersion"
BUILD_OLD = '        let build=Bundle.main.object(forInfoDictionaryKey:"CFBundleVersion") as? String ?? ""'
BUILD_NEW = "        let build=JerkgramReleaseIdentity.build"

PAYLOAD_OLD = '        var payload:[String:Any]=["schema":1,"appVersion":version,"build":build,"iosVersion":os,"iosMajor":major,"deviceRegion":region,"installAgeDays":age,"dayId":dayId,"weekId":weekId,"monthId":monthId]'
PAYLOAD_NEW = '''        let model=hardwareModel()
        var payload:[String:Any]=["schema":1,"appVersion":version,"build":build,"iosVersion":os,"iosMajor":major,"deviceRegion":region,"deviceModel":model,"installAgeDays":age,"dayId":dayId,"weekId":weekId,"monthId":monthId,"event":"app_active","ts":Int(now.timeIntervalSince1970),"analyticsDay":analyticsDay,"analyticsDayId":analyticsDayId,"openCountToday":openCountToday]'''

TASK_OLD = "        let task=URLSession.shared.dataTask(with:request)"
TASK_NEW = '''        defaults.set(now,forKey:lastAttemptAtKey)
        let task=URLSession.shared.dataTask(with:request)'''

LOCAL_SECRET_ANCHOR = "    private func localSecret(defaults:UserDefaults)->[UInt8]"
HARDWARE_MODEL_HELPER = '''    private func hardwareModel()->String {
        var info=utsname()
        guard uname(&info) == 0 else { return "unknown" }
        let capacity=MemoryLayout.size(ofValue:info.machine)
        return withUnsafePointer(to:&info.machine) { pointer in
            pointer.withMemoryRebound(to:CChar.self,capacity:capacity) { String(cString:$0) }
        }
    }
'''


def verify_transformed(text: str) -> None:
    lines = [line.strip() for line in text.splitlines()]
    require(lines.count(MARKER) == 1, "telemetry v2 marker count != 1")
    require(lines.count(ADDENDUM_MARKER) == 1, "telemetry v2.1 marker count != 1")
    require('https://jerkgram-telemetry.cronusk1809.workers.dev/v1/activity' in text, "telemetry endpoint changed")
    require('"schema":1' in text, "schema=1 disappeared")
    require('"dayId":dayId' in text and '"weekId":weekId' in text and '"monthId":monthId' in text, "legacy period IDs disappeared")
    require('payload["installReceiptId"]=receipt' in text, "installReceiptId disappeared")
    require("JerkgramReleaseIdentity.technicalVersion" in text, "technical Beta 2 identity is not used")
    require("JerkgramReleaseIdentity.build" in text, "Build133 identity is not used")
    require('forInfoDictionaryKey:"CFBundleShortVersionString"' not in text, "telemetry still reports Telegram 12.9.2 as appVersion")
    for field in ('"analyticsDay":analyticsDay', '"analyticsDayId":analyticsDayId', '"openCountToday":openCountToday'):
        require(field in text, "Telemetry v2 field missing: " + field)
    for field in ('"deviceModel":model', '"event":"app_active"', '"ts":Int(now.timeIntervalSince1970)'):
        require(field in text, "Telemetry v2.1 compatibility field missing: " + field)
    require('TimeZone(identifier: "Europe/Moscow")' in text, "Moscow analytics day missing")
    require('"jerkgram-msk-day-v1:"+analyticsDay' in text, "v2.1 Moscow day HMAC namespace missing")
    require("lastAttemptAtKey" in text and "defaults.set(now,forKey:lastAttemptAtKey)" in text, "attempt rate limit missing")
    require("applicationDidEnterBackground()" in text and "hasSeenActive" in text, "foreground lifecycle semantics missing")
    require("hardwareModel()" in text and "uname(&info)" in text, "device model owner missing")
    require(text.count("URLSession.shared.dataTask") == 1, "network owner count changed")
    require(text.count("private let endpoint = URL(") == 1, "endpoint owner count changed")
    require(text.count("guard JerkgramTelemetryPreferences.isEnabled else") >= 2, "OFF-before-network gates disappeared")


def patch_app_delegate_text(text: str) -> str:
    if MARKER in text:
        verify_transformed(text)
        return text

    require(BASE_MARKER in text, "Build130 telemetry baseline missing")
    text = ensure_darwin_import(text)
    text = replace_once(text, BASE_MARKER, BASE_MARKER + "\n" + MARKER + "\n" + ADDENDUM_MARKER, "telemetry marker")
    text = replace_once(text, KEY_ANCHOR, KEYS_NEW, "v2 storage keys")
    text = replace_once(text, ACTIVE_OLD, ACTIVE_NEW, "applicationDidBecomeActive owner")
    text = replace_once(text, HELPER_ANCHOR, HELPERS, "v2 helper insertion")
    text = replace_once(text, SECRET_ANCHOR, SECRET_NEW, "v2 payload derivation")
    text = replace_once(text, INTERVAL_OLD, INTERVAL_NEW, "v2.1 attempt rate limit")
    text = replace_once(text, VERSION_OLD, VERSION_NEW, "technical app version")
    text = replace_once(text, BUILD_OLD, BUILD_NEW, "build identity")
    text = replace_once(text, PAYLOAD_OLD, PAYLOAD_NEW, "payload fields")
    text = replace_once(text, TASK_OLD, TASK_NEW, "pre-network attempt timestamp")
    text = replace_once(text, LOCAL_SECRET_ANCHOR, HARDWARE_MODEL_HELPER + LOCAL_SECRET_ANCHOR, "device model helper")
    text = patch_background_lifecycle(text)
    verify_transformed(text)
    return text


def main() -> None:
    require(APP_DELEGATE.is_file(), "AppDelegate missing: " + str(APP_DELEGATE))
    APP_DELEGATE.write_text(patch_app_delegate_text(APP_DELEGATE.read_text(encoding="utf-8")), encoding="utf-8")
    print("[Build136 telemetry v2.1] SOURCE PATCHED")
    print("[Build136 telemetry v2.1] appVersion=1.0.2-beta.2 / build=136 / schema=1 / full legacy payload + Moscow day counters")


if __name__ == "__main__":
    main()
