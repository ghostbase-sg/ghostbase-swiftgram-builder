#!/usr/bin/env python3
from pathlib import Path
import sys


REGISTER_RELATIVE_PATH = Path("submodules/TelegramCore/Sources/TelegramEngine/AccountData/RegisterNotificationToken.swift")
ENGINE_RELATIVE_PATH = Path("submodules/TelegramCore/Sources/TelegramEngine/AccountData/TelegramEngineAccountData.swift")

REGISTER_ANCHOR = "func _internal_registerNotificationToken(account: Account, token: Data, type: NotificationTokenType, sandbox: Bool, otherAccountUserIds: [PeerId.Id], excludeMutedChats: Bool) -> Signal<Bool, NoError> {"
WEBPUSH_MARKER = "func _internal_registerWebPushNotificationToken(account: Account, subscriptionJson: String"

WEBPUSH_HELPER = '''func _internal_registerWebPushNotificationToken(account: Account, subscriptionJson: String, otherAccountUserIds: [PeerId.Id], excludeMutedChats: Bool) -> Signal<Bool, NoError> {
    var flags: Int32 = 0
    if excludeMutedChats {
        flags |= 1 << 0
    }
    return account.network.request(Api.functions.account.registerDevice(flags: flags, tokenType: 10, token: subscriptionJson, appSandbox: .boolFalse, secret: Buffer(data: Data()), otherUids: otherAccountUserIds.map({ $0._internalGetInt64Value() })))
    |> map { _ -> Bool in
        return true
    }
    |> `catch` { _ -> Signal<Bool, NoError> in
        return .single(false)
    }
}'''

ENGINE_NATIVE_BLOCK = '''        public func registerNotificationToken(token: Data, type: NotificationTokenType, sandbox: Bool, otherAccountUserIds: [PeerId.Id], excludeMutedChats: Bool) -> Signal<Bool, NoError> {
            return _internal_registerNotificationToken(account: self.account, token: token, type: type, sandbox: sandbox, otherAccountUserIds: otherAccountUserIds, excludeMutedChats: excludeMutedChats)
        }
'''

ENGINE_WEBPUSH_BLOCK = '''
        public func registerWebPushNotificationToken(subscriptionJson: String, otherAccountUserIds: [PeerId.Id], excludeMutedChats: Bool) -> Signal<Bool, NoError> {
            return _internal_registerWebPushNotificationToken(account: self.account, subscriptionJson: subscriptionJson, otherAccountUserIds: otherAccountUserIds, excludeMutedChats: excludeMutedChats)
        }
'''


def patch_register_source(source: str) -> str:
    if WEBPUSH_MARKER in source:
        if source.count(WEBPUSH_MARKER) != 1:
            raise RuntimeError("Web Push helper marker appears more than once")
        return source

    if source.count(REGISTER_ANCHOR) != 1:
        raise RuntimeError("Expected exactly one Telegram 12.9.2 notification registration anchor")

    if not source.endswith("\n"):
        raise RuntimeError("RegisterNotificationToken.swift has unexpected EOF shape")

    return source.rstrip("\n") + "\n\n" + WEBPUSH_HELPER + "\n"


def patch_engine_source(source: str) -> str:
    marker = "public func registerWebPushNotificationToken(subscriptionJson: String"
    if marker in source:
        if source.count(marker) != 1:
            raise RuntimeError("Web Push engine wrapper marker appears more than once")
        return source

    if source.count(ENGINE_NATIVE_BLOCK) != 1:
        raise RuntimeError("Expected exactly one TelegramEngine AccountData notification wrapper anchor")

    return source.replace(ENGINE_NATIVE_BLOCK, ENGINE_NATIVE_BLOCK + ENGINE_WEBPUSH_BLOCK, 1)


def patch_tree(root: Path) -> None:
    register_path = root / REGISTER_RELATIVE_PATH
    engine_path = root / ENGINE_RELATIVE_PATH
    if not register_path.is_file():
        raise RuntimeError(f"Missing source file: {register_path}")
    if not engine_path.is_file():
        raise RuntimeError(f"Missing source file: {engine_path}")

    register_original = register_path.read_text()
    engine_original = engine_path.read_text()
    register_patched = patch_register_source(register_original)
    engine_patched = patch_engine_source(engine_original)

    if register_patched != register_original:
        register_path.write_text(register_patched)
    if engine_patched != engine_original:
        engine_path.write_text(engine_patched)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} <telegram-ios-root>", file=sys.stderr)
        return 2
    try:
        patch_tree(Path(sys.argv[1]).resolve())
    except RuntimeError as error:
        print(f"webpush-poc patch failed: {error}", file=sys.stderr)
        return 1
    print("webpush-poc patch applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
