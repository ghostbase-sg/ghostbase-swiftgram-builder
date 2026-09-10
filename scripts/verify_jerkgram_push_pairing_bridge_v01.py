#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
APP_DELEGATE = ROOT / "submodules/TelegramUI/Sources/AppDelegate.swift"

errors = []
if not APP_DELEGATE.exists():
    errors.append(f"missing AppDelegate: {APP_DELEGATE}")
else:
    text = APP_DELEGATE.read_text()
    handler = "private func handleJerkgramPushPairingUrl(_ url: URL) -> Bool"
    external_handler = "private func handleJerkgramExternalUrl(_ url: URL) -> Bool"

    required = (
        handler,
        external_handler,
        'url.scheme?.lowercased() == "jerkgram"',
        'url.host?.lowercased() == "push"',
        'url.path == "/authorize"',
        "url.absoluteString.utf8.count <= 2048",
        "tokenItems.count == 1",
        "rawToken.count <= 1536",
        'case "A"..."Z", "a"..."z", "0"..."9", "-", "_"',
        "tokenData.count <= 1024",
        "guard let primary = activeAccounts.primary else",
        "transaction.getPeer(primary.account.peerId)",
        "as? TelegramUser",
        "user?.username",
        "[user.firstName, user.lastName]",
        "primary.engine.privacy.activeSessions()",
        "approveAuthTransferToken(",
        'UIAlertAction(title: "Cancel", style: .cancel)',
        'UIAlertAction(title: "Connect", style: .default',
        "Connection request expired. Try again.",
        "Could not connect to Telegram. Try again.",
        "self.window?.rootViewController?.present(",
    )
    for value in required:
        if value not in text:
            errors.append(f"AppDelegate missing invariant: {value}")

    if text.count(handler) != 1:
        errors.append(f"pairing handler count={text.count(handler)}, expected 1")
    if text.count(external_handler) != 1:
        errors.append(f"external dispatcher count={text.count(external_handler)}, expected 1")
    if text.count("if self.handleJerkgramExternalUrl(url)") != 3:
        errors.append(
            f"external URL callback dispatch count={text.count('if self.handleJerkgramExternalUrl(url)')}, expected 3"
        )

    legacy_expected = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?) -> Bool {\n        if self.handleJerkgramExternalUrl(url) {\n            return true\n        }\n        self.openUrl(url: url)\n        return true\n    }\n"""
    annotation_expected = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {\n        if self.handleJerkgramExternalUrl(url) {\n            return true\n        }\n        self.openUrl(url: url)\n        return true\n    }\n"""
    modern_expected = """    func application(_ app: UIPapplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool {\n        if self.handleJerkgramExternalUrl(url) {\n            return true\n        }\n        guard self.openUrlInProgress != url else {\n            return true\n        }\n        \n        self.openUrl(url: url)\n        return true\n    }\n"""
    for name, expected in (
        ("legacy sourceApplication", legacy_expected),
        ("annotation", annotation_expected),
        ("modern options", modern_expected),
    ):
        if text.count(expected) != 1:
            errors.append(f"{name} URL callback is not routed through the shared Jerkgram dispatcher exactly once")

    if handler in text and external_handler in text:
        pairing_start = text.index(handler)
        external_start = text.index(external_handler, pairing_start)
        pairing_scope = text[pairing_start:external_start]

        if pairing_scope.count("self.window?.rootViewController?.present(") != 4:
            errors.append("pairing helper must use exactly four UIKit root-view-controller presentations")

        for forbidden in (
            "UserDefaults",
            "print(rawToken)",
            "print(tokenData)",
            "print(url)",
            "mainWindow?.viewController?.present",
        ):
            if forbidden in pairing_scope:
                errors.append(f"pairing helper contains forbidden persistence/logging/presentation: {forbidden}")

        if 'url.path == "/authorize" else {\n            return false\n        }' not in pairing_scope:
            errors.append("pairing handler must reject non-/authorize routes without consuming them")
        if "Consume every malformed authorize request locally" not in pairing_scope:
            errors.append("pairing handler must retain malformed-authorize consumption contract")

        callback_start = text.index("func application(_ application: UIApplication, open url: URL", external_start)
        external_scope = text[external_start:callback_starut
        if "handleJerkgramPushPairingUrl(url)" not in external_scope or "handleJerkgramPushUrl(url)" not in external_scope:
            errors.append("shared external dispatcher must contain both /authorize and /open handlers")
        elif external_scope.index("handleJerkgramPushPairingUrl(url)") > external_scope.index("handleJerkgramPushUrl(url)"):
            errors.append("/authorize handler must run before /open handler")
    elif handler in text:
        errors.append("shared external URL dispatcher missing after pairing helper")

if errors:
    print("[jerkgram-push-pairing-verify] FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("[jerkgram-push-pairing-verify] PASS")
