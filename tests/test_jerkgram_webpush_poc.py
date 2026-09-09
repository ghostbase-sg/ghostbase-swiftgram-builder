import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PATCHER_PATH = REPO_ROOT / "scripts" / "apply_jerkgram_webpush_poc.py"
VERIFIER_PATH = REPO_ROOT / "scripts" / "verify_jerkgram_webpush_poc.py"

REGISTER_SOURCE = """import Foundation
import SwiftSignalKit
import Postbox
import TelegramApi


public enum NotificationTokenType {
    case aps(encrypt: Bool)
    case voip
}

func _internal_unregisterNotificationToken(account: Account, token: Data, type: NotificationTokenType, otherAccountUserIds: [PeerId.Id]) -> Signal<Never, NoError> {
    let mappedType: Int32
    switch type {
        case .aps:
            mappedType = 1
        case .voip:
            mappedType = 9
    }
    return account.network.request(Api.functions.account.unregisterDevice(tokenType: mappedType, token: hexString(token), otherUids: otherAccountUserIds.map({ $0._internalGetInt64Value() })))
    |> retryRequest
    |> ignoreValues
}

func _internal_registerNotificationToken(account: Account, token: Data, type: NotificationTokenType, sandbox: Bool, otherAccountUserIds: [PeerId.Id], excludeMutedChats: Bool) -> Signal<Bool, NoError> {
    return masterNotificationsKey(account: account, ignoreDisabled: false)
    |> mapToSignal { masterKey -> Signal<Bool, NoError> in
        let mappedType: Int32
        var keyData = Data()
        switch type {
            case let .aps(encrypt):
                mappedType = 1
                if encrypt {
                    keyData = masterKey.data
                }
            case .voip:
                mappedType = 9
                keyData = masterKey.data
        }
        var flags: Int32 = 0
        if excludeMutedChats {
            flags |= 1 << 0
        }
        return account.network.request(Api.functions.account.registerDevice(flags: flags, tokenType: mappedType, token: hexString(token), appSandbox: sandbox ? .boolTrue : .boolFalse, secret: Buffer(data: keyData), otherUids: otherAccountUserIds.map({ $0._internalGetInt64Value() })))
        |> map { _ -> Bool in
            return true
        }
        |> `catch` { error -> Signal<Bool, NoError> in
            if error.errorDescription == \"TOKEN_WAS_INVALIDATED\" {
                return .single(false)
            } else {
                return .single(true)
            }
        }
    }
}
"""

ENGINE_SOURCE = """import Foundation
import SwiftSignalKit
import Postbox
import TelegramApi

public extension TelegramEngine {
    final class AccountData {
        private let account: Account

        init(account: Account) {
            self.account = account
        }

        public func unregisterNotificationToken(token: Data, type: NotificationTokenType, otherAccountUserIds: [PeerId.Id]) -> Signal<Never, NoError> {
            return _internal_unregisterNotificationToken(account: self.account, token: token, type: type, otherAccountUserIds: otherAccountUserIds)
        }

        public func registerNotificationToken(token: Data, type: NotificationTokenType, sandbox: Bool, otherAccountUserIds: [PeerId.Id], excludeMutedChats: Bool) -> Signal<Bool, NoError> {
            return _internal_registerNotificationToken(account: self.account, token: token, type: type, sandbox: sandbox, otherAccountUserIds: otherAccountUserIds, excludeMutedChats: excludeMutedChats)
        }

        public func updateAccountPhoto(resource: EngineMediaResource?) {
        }
    }
}
"""


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WebPushNativePatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patcher = load_module(PATCHER_PATH, "apply_jerkgram_webpush_poc")

    def test_register_patch_adds_separate_raw_json_type10_path(self):
        patched = self.patcher.patch_register_source(REGISTER_SOURCE)
        self.assertIn("func _internal_registerWebPushNotificationToken", patched)
        self.assertIn("tokenType: 10", patched)
        self.assertIn("token: subscriptionJson", patched)
        self.assertIn("appSandbox: .boolFalse", patched)
        self.assertIn("secret: Buffer(data: Data())", patched)

        helper = patched.split("func _internal_registerWebPushNotificationToken", 1)[1]
        self.assertNotIn("hexString(subscriptionJson", helper)
        self.assertNotIn("hexString(token)", helper)

    def test_existing_native_aps_and_voip_registration_is_unchanged(self):
        patched = self.patcher.patch_register_source(REGISTER_SOURCE)
        original_native = REGISTER_SOURCE.split("func _internal_registerNotificationToken", 1)[1]
        patched_native = patched.split("func _internal_registerNotificationToken", 1)[1]
        patched_native = patched_native.split("\nfunc _internal_registerWebPushNotificationToken", 1)[0]
        self.assertEqual(original_native.rstrip(), patched_native.rstrip())
        self.assertIn("mappedType = 1", patched_native)
        self.assertIn("mappedType = 9", patched_native)
        self.assertIn("token: hexString(token)", patched_native)

    def test_engine_patch_adds_public_wrapper(self):
        patched = self.patcher.patch_engine_source(ENGINE_SOURCE)
        self.assertIn("public func registerWebPushNotificationToken", patched)
        self.assertIn("subscriptionJson: String", patched)
        self.assertIn("_internal_registerWebPushNotificationToken(account: self.account", patched)

    def test_patches_are_idempotent(self):
        once = self.patcher.patch_register_source(REGISTER_SOURCE)
        twice = self.patcher.patch_register_source(once)
        self.assertEqual(once, twice)
        once_engine = self.patcher.patch_engine_source(ENGINE_SOURCE)
        twice_engine = self.patcher.patch_engine_source(once_engine)
        self.assertEqual(once_engine, twice_engine)

    def test_register_patch_fails_closed_when_anchor_changes(self):
        changed = REGISTER_SOURCE.replace(
            "func _internal_registerNotificationToken(account: Account, token: Data, type: NotificationTokenType, sandbox: Bool, otherAccountUserIds: [PeerId.Id], excludeMutedChats: Bool)",
            "func _internal_registerNotificationToken_CHANGED(account: Account, token: Data, type: NotificationTokenType, sandbox: Bool, otherAccountUserIds: [PeerId.Id], excludeMutedChats: Bool)",
        )
        with self.assertRaises(RuntimeError):
            self.patcher.patch_register_source(changed)


class WebPushPwaStaticTests(unittest.TestCase):
    def test_pwa_uses_telegram_web_k_public_key_and_standard_subscription(self):
        html = (REPO_ROOT / "webpush-poc" / "site" / "index.html").read_text()
        key = "BB3JzmQIBTl8ZdTmLzhkZVnoYxoSvUmCe1CqqF53u2j0WbEFo2m--mOBagroDFdqMeESfz3ue1Z1e5PTIxMYH_g"
        self.assertEqual(html.count(key), 1)
        self.assertIn("navigator.serviceWorker.register", html)
        self.assertIn("pushManager.subscribe", html)
        self.assertIn("userVisibleOnly: true", html)
        self.assertIn("applicationServerKey", html)
        self.assertIn("subscription.toJSON()", html)
        self.assertNotIn("VAPID_PRIVATE", html)
        self.assertNotIn("privateKey", html)

    def test_service_worker_displays_push_and_handles_click(self):
        sw = (REPO_ROOT / "webpush-poc" / "site" / "sw.js").read_text()
        self.assertIn("addEventListener('push'", sw)
        self.assertIn("showNotification", sw)
        self.assertIn("addEventListener('notificationclick'", sw)
        self.assertNotIn("api_id", sw)
        self.assertNotIn("api_hash", sw)

    def test_manifest_is_standalone_and_scoped_locally(self):
        manifest = json.loads((REPO_ROOT / "webpush-poc" / "site" / "manifest.webmanifest").read_text())
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["start_url"], "./")
        self.assertEqual(manifest["scope"], "./")


class WebPushVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patcher = load_module(PATCHER_PATH, "apply_jerkgram_webpush_poc_for_verify")
        cls.verifier = load_module(VERIFIER_PATH, "verify_jerkgram_webpush_poc")

    def test_verifier_accepts_patched_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            register = root / self.patcher.REGISTER_RELATIVE_PATH
            engine = root / self.patcher.ENGINE_RELATIVE_PATH
            register.parent.mkdir(parents=True, exist_ok=True)
            engine.parent.mkdir(parents=True, exist_ok=True)
            register.write_text(self.patcher.patch_register_source(REGISTER_SOURCE))
            engine.write_text(self.patcher.patch_engine_source(ENGINE_SOURCE))
            self.verifier.verify_tree(root)

    def test_verifier_rejects_hex_encoded_webpush_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            register = root / self.patcher.REGISTER_RELATIVE_PATH
            engine = root / self.patcher.ENGINE_RELATIVE_PATH
            register.parent.mkdir(parents=True, exist_ok=True)
            engine.parent.mkdir(parents=True, exist_ok=True)
            bad = self.patcher.patch_register_source(REGISTER_SOURCE).replace(
                "token: subscriptionJson",
                "token: hexString(Data(subscriptionJson.utf8))",
            )
            register.write_text(bad)
            engine.write_text(self.patcher.patch_engine_source(ENGINE_SOURCE))
            with self.assertRaises(RuntimeError):
                self.verifier.verify_tree(root)


if __name__ == "__main__":
    unittest.main()
