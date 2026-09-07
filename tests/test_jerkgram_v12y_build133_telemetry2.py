from pathlib import Path
import importlib.util
import unittest


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts/apply_jerkgram_v12y_build133_telemetry2.py"
VERIFY = REPO / "scripts/verify_jerkgram_v12y_build133_telemetry2.py"


APP_FIXTURE = r'''
// MARK: Jerkgram v1.2T BUILD130_TELEMETRY1
private enum JerkgramTelemetryPreferences {
    static var isEnabled: Bool { true }
}
private final class JerkgramTelemetry {
    private let endpoint = URL(string: "https://jerkgram-telemetry.cronusk1809.workers.dev/v1/activity")!
    private let secretKey = "jerkgram.telemetry.secret.v1"
    private let firstDateKey = "jerkgram.telemetry.firstDate.v1"
    private let receiptKey = "jerkgram.telemetry.installReceipt.v1"
    private let installReportedKey = "jerkgram.telemetry.installReported.v1"
    private let lastSuccessKey = "jerkgram.telemetry.lastSuccess.v1"
    private let minimumInterval: TimeInterval = 4 * 60 * 60
    func applicationDidBecomeActive() { queue.async { [weak self] in self?.submitIfNeeded() } }
    private func submitIfNeeded() {
        guard JerkgramTelemetryPreferences.isEnabled else { return }
        let defaults = UserDefaults.standard; let now = Date()
        guard activeTask == nil else { return }
        let secret = localSecret(defaults: defaults)
        let dayId=hmac(secret,"day")
        let weekId=hmac(secret,"week")
        let monthId=hmac(secret,"month")
        let receipt="receipt"
        let version=Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? ""
        let build=Bundle.main.object(forInfoDictionaryKey:"CFBundleVersion") as? String ?? ""
        let os=UIDevice.current.systemVersion; let major=0
        let region="ZZ"
        let age=0
        var payload:[String:Any]=["schema":1,"appVersion":version,"build":build,"iosVersion":os,"iosMajor":major,"deviceRegion":region,"installAgeDays":age,"dayId":dayId,"weekId":weekId,"monthId":monthId]
        if !defaults.bool(forKey:installReportedKey){payload["installReceiptId"]=receipt}
        guard let body=try? JSONSerialization.data(withJSONObject:payload) else{return}
        var request=URLRequest(url:endpoint);request.httpMethod="POST";request.httpBody=body
        guard JerkgramTelemetryPreferences.isEnabled else{return}
        let task=URLSession.shared.dataTask(with:request){_,_,_ in}
        activeTask=task;task.resume()
    }
    private func localSecret(defaults:UserDefaults)->[UInt8]{[]}
    private func hmac(_ key:[UInt8],_ value:String)->String{"id"}
}
'''


class Build133TelemetryV2Tests(unittest.TestCase):
    def load_patch(self):
        spec = importlib.util.spec_from_file_location("build133_telemetry2", PATCH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_payload_uses_beta2_shared_release_identity_and_keeps_legacy_ids(self):
        module = self.load_patch()
        updated = module.patch_app_delegate_text(APP_FIXTURE)
        self.assertIn("JerkgramReleaseIdentity.technicalVersion", updated)
        self.assertIn("JerkgramReleaseIdentity.build", updated)
        self.assertNotIn('forInfoDictionaryKey:"CFBundleShortVersionString"', updated)
        for token in (
            '"schema":1',
            '"dayId":dayId',
            '"weekId":weekId',
            '"monthId":monthId',
            'payload["installReceiptId"]=receipt',
            '"analyticsDay":analyticsDay',
            '"analyticsDayId":analyticsDayId',
            '"openCountToday":openCountToday',
            'https://jerkgram-telemetry.cronusk1809.workers.dev/v1/activity',
        ):
            self.assertIn(token, updated)

    def test_off_gate_and_single_network_owner_are_preserved(self):
        module = self.load_patch()
        updated = module.patch_app_delegate_text(APP_FIXTURE)
        self.assertGreaterEqual(updated.count("guard JerkgramTelemetryPreferences.isEnabled else"), 2)
        self.assertEqual(updated.count("URLSession.shared.dataTask"), 1)
        self.assertEqual(updated.count("private let endpoint = URL("), 1)

    def test_moscow_open_counter_is_additive(self):
        module = self.load_patch()
        updated = module.patch_app_delegate_text(APP_FIXTURE)
        for token in (
            'TimeZone(identifier: "Europe/Moscow")',
            'jerkgram.telemetry.analyticsDay.v2',
            'jerkgram.telemetry.openCountToday.v2',
            'recordOpen()',
            'analyticsDayId=hmac(secret,"analytics-day:"+analyticsDay)',
        ):
            self.assertIn(token, updated)

    def test_materialized_verifier_checks_identity_privacy_and_v2_fields(self):
        source = VERIFY.read_text(encoding="utf-8")
        for token in (
            "verify_telemetry_owner",
            "JerkgramReleaseIdentity.technicalVersion",
            "JerkgramReleaseIdentity.build",
            "analyticsDay",
            "analyticsDayId",
            "openCountToday",
            "installReceiptId",
            "URLSession.shared.dataTask",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
