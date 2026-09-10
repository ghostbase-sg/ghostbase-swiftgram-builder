#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
APP_DELEGATE = ROOT / "submodules/TelegramUI/Sources/AppDelegate.swift"

if not APP_DELEGATE.exists():
    raise SystemExit(f"[jerkgram-push-pairing] missing {APP_DELEGATE}")

text = APP_DELEGATE.read_text()
marker = "private func handleJerkgramPushPairingUrl(_ url: URL) -> Bool"

# This script is intentionally layered after apply_jerkgram_push_click_bridge_v01.py.
# That bridge owns the dedicated jerkgram:// scheme and the final open-url dispatch.
dispatch_anchor = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {\n        if self.handleJerkgramPushUrl(url) {\n            return true\n        }\n        self.openUrl(url: url)\n        return true\n    }\n"""

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

'''

if marker not in text:
    if text.count(dispatch_anchor) != 1:
        raise SystemExit(f"[jerkgram-push-pairing] expected one click bridge dispatch anchor, found {text.count(dispatch_anchor)}")
    text = text.replace(dispatch_anchor, helper + dispatch_anchor, 1)

paired_dispatch = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {\n        if self.handleJerkgramPushPairingUrl(url) {\n            return true\n        }\n        if self.handleJerkgramPushUrl(url) {\n            return true\n        }\n        self.openUrl(url: url)\n        return true\n    }\n"""

if paired_dispatch not in text:
    if text.count(dispatch_anchor) != 1:
        raise SystemExit(f"[jerkgram-push-pairing] expected one dispatch anchor, found {text.count(dispatch_anchor)}")
    text = text.replace(dispatch_anchor, paired_dispatch, 1)

for invariant in (
    marker,
    'url.scheme?.lowercased() == "jerkgram"',
    'url.host?.lowercased() == "push"',
    'url.path == "/authorize"',
    "tokenItems.count == 1",
    "transaction.getPeer(primary.account.peerId)",
    "approveAuthTransferToken(",
    "Connection request expired. Try again.",
    "Could not connect to Telegram. Try again.",
    "self.window?.rootViewController?.present(",
    "if self.handleJerkgramPushPairingUrl(url)",
):
    if invariant not in text:
        raise SystemExit(f"[jerkgram-push-pairing] invariant missing after patch: {invariant}")

if text.count(marker) != 1:
    raise SystemExit(f"[jerkgram-push-pairing] pairing handler count is {text.count(marker)}, expected 1")

# Presentation assertions are deliberately scoped to our helper. Stock Telegram's
# AppDelegate has its own legitimate rootViewController.present calls.
helper_start = text.index(marker)
dispatch_start = text.index(
    "func application(_ application: UIApplication, open url: URL",
    helper_start,
)
helper_scope = text[helper_start:dispatch_start]

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
