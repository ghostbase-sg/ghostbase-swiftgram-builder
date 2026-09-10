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
    required = (
        handler,
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
        "if self.handleJerkgramPushPairingUrl(url)",
    )
    for value in required:
        if value not in text:
            errors.append(f"AppDelegate missing invariant: {value}")

    if text.count(handler) != 1:
        errors.append(f"pairing handler count={text.count(handler)}, expected 1")
    if text.count("if self.handleJerkgramPushPairingUrl(url)") != 1:
        errors.append("pairing dispatch must exist exactly once")

    dispatch_signature = "func application(_ application: UIApplication, open url: URL"
    if handler in text and dispatch_signature in text:
        helper_start = text.index(handler)
        dispatch_start = text.index(dispatch_signature, helper_start)
        helper_scope = text[helper_start:dispatch_start]

        if helper_scope.count("self.window?.rootViewController?.present(") != 4:
            errors.append("pairing helper must use exactly four UIKit root-view-controller presentations")
        if "self.mainWindow?.viewController?.present(" in helper_scope:
            errors.append("pairing helper must not call present on ContainableController")

        for forbidden in (
            "UserDefaults",
            "print(rawToken)",
            "print(tokenData)",
            "mainWindow?.viewController?.present",
        ):
            if forbidden in helper_scope:
                errors.append(f"pairing helper contains forbidden persistence/logging/presentation: {forbidden}")

        dispatch = text[dispatch_start:]
        if "handleJerkgramPushPairingUrl(url)" in dispatch and "handleJerkgramPushUrl(url)" in dispatch:
            if dispatch.index("handleJerkgramPushPairingUrl(url)") > dispatch.index("handleJerkgramPushUrl(url)"):
                errors.append("/authorize handler must run before /open handler")
    elif handler in text:
        errors.append("open-url dispatch signature missing after pairing helper")

if errors:
    print("[jerkgram-push-pairing-verify] FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("[jerkgram-push-pairing-verify] PASS")
