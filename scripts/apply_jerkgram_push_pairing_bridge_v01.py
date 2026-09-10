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
              let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let rawToken = components.queryItems?.first(where: { $0.name == "token" })?.value,
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
                guard let self = self, let primary = activeAccounts.primary else {
                    return
                }

                let alert = UIAlertController(
                    title: "Jerkgram Notifications",
                    message: "Connect this Telegram account to Jerkgram Notifications? This creates a separate companion session used only for Web Push.",
                    preferredStyle: .alert
                )
                alert.addAction(UIAlertAction(title: "Cancel", style: .cancel))
                alert.addAction(UIAlertAction(title: "Connect", style: .default, handler: { [weak self] _ in
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
                            message: "Connected. Return to Jerkgram Notifications to finish enabling Web Push.",
                            preferredStyle: .alert
                        )
                        done.addAction(UIAlertAction(title: "OK", style: .default))
                        self.mainWindow?.viewController?.present(done, animated: true)
                    }, error: { [weak self] _ in
                        guard let self = self else {
                            return
                        }
                        let failed = UIAlertController(
                            title: "Jerkgram Notifications",
                            message: "The pairing token is invalid, expired, or was already used. Start pairing again from Jerkgram Notifications.",
                            preferredStyle: .alert
                        )
                        failed.addAction(UIAlertAction(title: "OK", style: .default))
                        self.mainWindow?.viewController?.present(failed, animated: true)
                    })
                }))
                self.mainWindow?.viewController?.present(alert, animated: true)
            })
        })

        return true
    }

'''

if marker not in text:
    if dispatch_anchor not in text:
        raise SystemExit("[jerkgram-push-pairing] click bridge dispatch anchor not found; apply click bridge first")
    text = text.replace(dispatch_anchor, helper + dispatch_anchor, 1)

paired_dispatch = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {\n        if self.handleJerkgramPushPairingUrl(url) {\n            return true\n        }\n        if self.handleJerkgramPushUrl(url) {\n            return true\n        }\n        self.openUrl(url: url)\n        return true\n    }\n"""

if paired_dispatch not in text:
    if dispatch_anchor not in text:
        raise SystemExit("[jerkgram-push-pairing] dispatch anchor not found")
    text = text.replace(dispatch_anchor, paired_dispatch, 1)

APP_DELEGATE.write_text(text)
print("[jerkgram-push-pairing] OK")
print("  patched:", APP_DELEGATE)
