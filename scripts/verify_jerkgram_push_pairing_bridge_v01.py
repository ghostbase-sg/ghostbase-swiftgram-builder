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
    pairing_handler = "private func handleJerkgramPushPairingUrl(_ url: URL) -> Bool"
    dispatcher = "private func handleJerkgramExternalUrl(_ url: URL) -> Bool"

    required = (
        pairing_handler,
        dispatcher,
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

    if text.count(pairing_handler) != 1:
        errors.append(f"pairing handler count={text.count(pairing_handler)}, expected 1")
    if text.count(dispatcher) != 1:
        errors.append(f"external dispatcher count={text.count(dispatcher)}, expected 1")

    # Pairing routing must classify /authorize before any token validation so that
    # malformed authorize URLs are consumed instead of reaching Telegram openUrl.
    if pairing_handler in text and dispatcher in text:
        pair_start = text.index(pairing_handler)
        dispatcher_start = text.index(dispatcher, pair_start)
        pair_scope = text[pair_start:dispatcher_start]

        route_marker = 'url.path == "/authorize" else'
        validation_marker = "guard url.absoluteString.utf8.count <= 2048"
        if route_marker not in pair_scope or validation_marker not in pair_scope:
            errors.append("pairing helper route/validation guards are incomplete")
        elif pair_scope.index(route_marker) > pair_scope.index(validation_marker):
            errors.append("/authorize route must be matched before token validation")

        if "self.mainWindow?.viewController?.present(" in pair_scope:
            errors.append("pairing helper must not call present on ContainableController")
        if pair_scope.count("self.window?.rootViewController?.present(") != 4:
            errors.append("pairing helper must use exactly four UIKit root-view-controller presentations")

        for forbidden in (
            "UserDefaults",
            "print(",
            "NSLog(",
            "os_log(",
            "Logger(",
        ):
            if forbidden in pair_scope:
                errors.append(f"pairing helper contains forbidden persistence/token logging primitive: {forbidden}")

        next_callback_marker = "func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool"
        if next_callback_marker not in text:
            errors.append("annotation external URL callback missing")
        else:
            next_callback = text.index(next_callback_marker, dispatcher_start)
            dispatch_scope = text[dispatcher_start:next_callback]
            pair_call = "self.handleJerkgramPushPairingUrl(url)"
            click_call = "self.handleJerkgramPushUrl(url)"
            if dispatch_scope.count(pair_call) != 1 or dispatch_scope.count(click_call) != 1:
                errors.append("unified dispatcher must call pairing and click handlers exactly once")
            elif dispatch_scope.index(pair_call) > dispatch_scope.index(click_call):
                errors.append("unified dispatcher must check /authorize before /open")
            if "self.openUrl(url: url)" in dispatch_scope:
                errors.append("unified dispatcher must not call Telegram generic openUrl")

    callback_signatures = (
        "func application(_ application: UIApplication, open url: URL, sourceApplication: String?) -> Bool",
        "func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool",
        "func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool",
    )

    def callback_scope(signature: str):
        if signature not in text:
            errors.append(f"external URL callback missing: {signature}")
            return None
        start = text.index(signature)
        body_start = text.index("{", start)
        depth = 0
        for index in range(body_start, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    return text[start:index + 1]
        errors.append(f"unterminated external URL callback: {signature}")
        return None

    for signature in callback_signatures:
        scope = callback_scope(signature)
        if scope is None:
            continue
        dispatch_call = "self.handleJerkgramExternalUrl(url)"
        generic_call = "self.openUrl(url: url)"
        if scope.count(dispatch_call) != 1:
            errors.append(f"callback must call unified Jerkgram dispatcher exactly once: {signature}")
        if generic_call not in scope:
            errors.append(f"callback lost Telegram generic openUrl fallback: {signature}")
        if dispatch_call in scope and generic_call in scope and scope.index(dispatch_call) > scope.index(generic_call):
            errors.append(f"Jerkgram dispatcher must run before Telegram generic openUrl: {signature}")
        if "self.handleJerkgramPushPairingUrl(url)" in scope or "self.handleJerkgramPushUrl(url)" in scope:
            errors.append(f"callback must use only the unified Jerkgram dispatcher: {signature}")

    modern_signature = "func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool"
    modern_scope = callback_scope(modern_signature) if modern_signature in text else None
    if modern_scope is not None:
        dispatch_call = "self.handleJerkgramExternalUrl(url)"
        progress_guard = "guard self.openUrlInProgress != url else"
        generic_call = "self.openUrl(url: url)"
        if progress_guard not in modern_scope:
            errors.append("modern callback lost Telegram openUrlInProgress guard")
        elif dispatch_call in modern_scope and generic_call in modern_scope:
            if not (modern_scope.index(dispatch_call) < modern_scope.index(progress_guard) < modern_scope.index(generic_call)):
                errors.append("modern callback order must be Jerkgram dispatch -> openUrlInProgress -> Telegram openUrl")

if errors:
    print("[jerkgram-push-pairing-verify] FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("[jerkgram-push-pairing-verify] PASS")
