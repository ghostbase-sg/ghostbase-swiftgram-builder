#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
APP_DELEGATE = ROOT / "submodules/TelegramUI/Sources/AppDelegate.swift"

if not APP_DELEGATE.exists():
    raise SystemExit(f"[jerkgram-push-pairing] missing {APP_DELEGATE}")

text = APP_DELEGATE.read_text()
marker = "private func handleJerkgramPushPairingUrl(_ url: URL) -> Bool"
external_marker = "private func handleJerkgramExternalUrl(_ url: URL) -> Bool"

# This script is intentionally layered after apply_jerkgram_push_click_bridge_v01.py.
# The click bridge owns jerkgram:// registration and /push/open semantics. This
# layer adds /push/authorize and makes one shared Jerkgram dispatch reachable from
# every external-URL UIApplicationDelegate entrypoint present in Telegram 12.9.2.
click_annotation_anchor = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {\n        if self.handleJerkgramPushUrl(url) {\n            return true\n        }\n        self.openUrl(url: url)\n        return true\n    }\n"""

helper = r'''    // MARK: Jerkgram Push Companion one-tap authorization bridge
    private func handleJerkgramPushPairingUrl(_ url: URL) -> Bool {
        guard url.scheme?.lowercased() == "jerkgram",
              url.host?.lowercased() == "push",
              url.path == "/authorize" else {
            return false
        }

        // Consume every malformed authorize request locally. Never pass a pairing
        // token into Telegram's generic URL router or log it as a normal URL.
        guard url.absoluteString.utf8.count <= 2048,
              let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            return true
        }

        let queryItems = components.queryItems ?? []
        let tokenItems = queryItems.filter({ $0.name == "token" })
        guard queryItems.allSatisfy({ $0.name == "token" }),
              tokenItems.count == 1,
              let rawToken = tokenItems[0].value,
              !rawToken.isEmpty,
              rawToken.count <= 1536,
              rawToken.allSatisfy({ character in
                  switch character {
                  case "A"..."Z", "a"..."z", "0"..."9", "-", "_":
                      return true
                  default:
                      return false
                  }
              }) else {
            return true
        }

        var base64 = rawToken.replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")
        while base64.count % 4 != 0 {
            base64.append("=")
        }
        guard let tokenData = Data(base64Encoded: base64),
              !tokenData.isEmpty,
              tokenData.count <= 1024 else {
            return true
        }

        let _ = (self.sharedContextPromise.get()
        |> take(1)
        |> deliverOnMainQueue).start(next: { [weak self] sharedApplicationContext in
            guard let self = self else {
                return
            }
            let _ = (sharedApplicationContext.sharedContext.activeAccountContexts
            |> take(1)
            |> deliverOnMainQueue).start(next: { [weak self] activeAccounts in
                guard let self = self else {
                    return
                }
                guard let primary = activeAccounts.primary else {
                    let failed = UIAlertController(
                        title: "Jerkgram Notifications",
                        message: "Could not connect to Telegram. Try again.",
                        preferredStyle: .alert
                    )
                    failed.addAction(UIAlertAction(title: "OK", style: .default))
                    self.window?.rootViewController?.present(failed, animated: true)
                    return
                }

                // Variant A for Alpha: use Telegram's current primary account. Read
                // its peer only to make the confirmation explicit; no account state
                // or session material is copied into the pairing URL or PWA.
                let _ = (primary.account.postbox.transaction { transaction -> TelegramUser? in
                    return transaction.getPeer(primary.account.peerId) as? TelegramUser
                }
                |> take(1)
                |> deliverOnMainQueue).start(next: { [weak self] user in
                    guard let self = self else {
                        return
                    }

                    let accountLabel: String
                    if let username = user?.username, !username.isEmpty {
                        accountLabel = "@\(username)"
                    } else if let user = user {
                        let displayName = [user.firstName, user.lastName]
                            .compactMap({ value -> String? in
                                guard let value = value, !value.isEmpty else {
                                    return nil
                                }
                                return value
                            })
                            .joined(separator: " ")
                        accountLabel = displayName.isEmpty ? "Current Telegram account" : displayName
                    } else {
                        accountLabel = "Current Telegram account"
                    }

                    let alert = UIAlertController(
                        title: "Jerkgram Notifications",
                        message: "Allow Jerkgram Notifications to connect to \(accountLabel)?\n\nA separate Telegram session will be created for notifications. Jerkgram Notifications does not receive the keys of this Jerkgram session.",
                        preferredStyle: .alert
                    )
                    alert.addAction(UIAlertAction(title: "Cancel", style: .cancel))
                    alert.addAction(UIAlertAction(title: "Connect", style: .default, handler: { [weak self] _ in
                        guard let self = self else {
                            return
                        }
                        let activeSessionsContext = primary.engine.privacy.activeSessions()
                        let _ = (approveAuthTransferToken(
                            account: primary.account,
                            token: tokenData,
                            activeSessionsContext: activeSessionsContext
                        )
                        |> deliverOnMainQueue).start(next: { [weak self] _ in
                            guard let self = self else {
                                return
                            }
                            let done = UIAlertController(
                                title: "Jerkgram Notifications",
                                message: "Jerkgram Notifications connected. Return to the notification setup to continue.",
                                preferredStyle: .alert
                            )
                            done.addAction(UIAlertAction(title: "OK", style: .default))
                            self.window?.rootViewController?.present(done, animated: true)
                        }, error: { [weak self] error in
                            guard let self = self else {
                                return
                            }
                            let message: String
                            switch error {
                            case .expired, .alreadyAccepted:
                                message = "Connection request expired. Try again."
                            case .invalid, .generic:
                                message = "Could not connect to Telegram. Try again."
                            }
                            let failed = UIAlertController(
                                title: "Jerkgram Notifications",
                                message: message,
                                preferredStyle: .alert
                            )
                            failed.addAction(UIAlertAction(title: "OK", style: .default))
                            self.window?.rootViewController?.present(failed, animated: true)
                        })
                    }))
                    self.window?.rootViewController?.present(alert, animated: true)
                })
            })
        })

        return true
    }

    // One bounded dispatch shared by every Telegram external-URL callback.
    // /authorize has priority over /open; all other URLs fall through unchanged.
    private func handleJerkgramExternalUrl(_ url: URL) -> Bool {
        if self.handleJerkgramPushPairingUrl(url) {
            return true
        }
        if self.handleJerkgramPushUrl(url) {
            return true
        }
        return false
    }

'''

if marker not in text:
    if text.count(click_annotation_anchor) != 1:
        raise SystemExit(
            f"[jerkgram-push-pairing] expected one click bridge dispatch anchor, found {text.count(click_annotation_anchor)}"
        )
    text = text.replace(click_annotation_anchor, helper + click_annotation_anchor, 1)
elif external_marker not in text:
    raise SystemExit("[jerkgram-push-pairing] pairing helper exists without shared external URL dispatcher")

legacy_anchor = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?) -> Bool {\n        self.openUrl(url: url)\n        return true\n    }\n"""
legacy_patched = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?) -> Bool {\n        if self.handleJerkgramExternalUrl(url) {\n            return true\n        }\n        self.openUrl(url: url)\n        return true\n    }\n"""

annotation_patched = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {\n        if self.handleJerkgramExternalUrl(url) {\n            return true\n        }\n        self.openUrl(url: url)\n        return true\n    }\n"""

modern_anchor = """    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool {\n        guard self.openUrlInProgress != url else {\n            return true\n        }\n        \n        self.openUrl(url: url)\n        return true\n    }\n"""
modern_patched = """    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool {\n        if self.handleJerkgramExternalUrl(url) {\n            return true\n        }\n        guard self.openUrlInProgress != url else {\n            return true\n        }\n        \n        self.openUrl(url: url)\n        return true\n    }\n"""

for name, original, patched in (
    ("legacy sourceApplication", legacy_anchor, legacy_patched),
    ("annotation", click_annotation_anchor, annotation_patched),
    ("modern options", modern_anchor, modern_patched),
):
    if patched not in text:
        if text.count(original) != 1:
            raise SystemExit(
                f"[jerkgram-push-pairing] expected one {name} URL entrypoint anchor, found {text.count(original)}"
            )
        text = text.replace(original, patched, 1)

for invariant in (
    marker,
    external_marker,
    'url.scheme?.lowercased() == "jerkgram"',
    'url.host?.lowercased() == "push"',
    'url.path == "/authorize"',
    "tokenItems.count == 1",
    "transaction.getPeer(primary.account.peerId)",
    "approveAuthTransferToken(",
    "Connection request expired. Try again.",
    "Could not connect to Telegram. Try again.",
    "self.window?.rootViewController?.present(",
    "if self.handleJerkgramExternalUrl(url)",
):
    if invariant not in text:
        raise SystemExit(f"[jerkgram-push-pairing] invariant missing after patch: {invariant}")

if text.count(marker) != 1:
    raise SystemExit(f"[jerkgram-push-pairing] pairing handler count is {text.count(marker)}, expected 1")
if text.count(external_marker) != 1:
    raise SystemExit(f"[jerkgram-push-pairing] external dispatcher count is {text.count(external_marker)}, expected 1")
if text.count("if self.handleJerkgramExternalUrl(url)") != 3:
    raise SystemExit(
        f"[jerkgram-push-pairing] external URL dispatch count is {text.count('if self.handleJerkgramExternalUrl(url)')}, expected 3"
    )

# Presentation assertions are deliberately scoped to our pairing helper. Stock
# Telegram's AppDelegate has its own legitimate rootViewController.present calls.
helper_start = text.index(marker)
external_start = text.index(external_marker, helper_start)
helper_scope = text[helper_start:external_start]

invalid_presentation = "self.mainWindow?.viewController?.present("
if invalid_presentation in helper_scope:
    raise SystemExit("[jerkgram-push-pairing] invalid ContainableController alert presentation survived")

presentation = "self.window?.rootViewController?.present("
if helper_scope.count(presentation) != 4:
    raise SystemExit(
        f"[jerkgram-push-pairing] helper UIKit alert presentation count is {helper_scope.count(presentation)}, expected 4"
    )

APP_DELEGATE.write_text(text)
print("[jerkgram-push-pairing] OK")
print("  patched:", APP_DELEGATE)
