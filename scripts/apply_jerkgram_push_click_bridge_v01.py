#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
APP_DELEGATE = ROOT / "submodules/TelegramUI/Sources/AppDelegate.swift"
INFO_BAZEL = ROOT / "Telegram/Telegram-iOS/InfoBazel.plist"
INFO_PLIST = ROOT / "Telegram/Telegram-iOS/Info.plist"
BUILD = ROOT / "Telegram/BUILD"

for path in (APP_DELEGATE, INFO_BAZEL, INFO_PLIST, BUILD):
    if not path.exists():
        raise SystemExit(f"[jerkgram-push-click] missing {path}")


def patch_plist(path: Path) -> None:
    text = path.read_text()
    if "<string>jerkgram</string>" in text:
        return
    anchor = """\t\t<dict>\n\t\t\t<key>CFBundleTypeRole</key>\n\t\t\t<string>Viewer</string>\n\t\t\t<key>CFBundleURLName</key>\n\t\t\t<string>$(PRODUCT_BUNDLE_IDENTIFIER).compatibility</string>\n"""
    if anchor not in text:
        raise SystemExit(f"[jerkgram-push-click] plist URL anchor not found in {path}")
    entry = """\t\t<dict>\n\t\t\t<key>CFBundleTypeRole</key>\n\t\t\t<string>Viewer</string>\n\t\t\t<key>CFBundleURLName</key>\n\t\t\t<string>$(PRODUCT_BUNDLE_IDENTIFIER).jerkgram</string>\n\t\t\t<key>CFBundleURLSchemes</key>\n\t\t\t<array>\n\t\t\t\t<string>jerkgram</string>\n\t\t\t</array>\n\t\t</dict>\n"""
    path.write_text(text.replace(anchor, entry + anchor, 1))


def patch_build(path: Path) -> None:
    text = path.read_text()
    if "<string>jerkgram</string>" in text:
        return
    anchor = """        <dict>\n            <key>CFBundleTypeRole</key>\n            <string>Viewer</string>\n            <key>CFBundleURLName</key>\n            <string>{telegram_bundle_id}.compatibility</string>\n"""
    if anchor not in text:
        raise SystemExit(f"[jerkgram-push-click] BUILD URL anchor not found in {path}")
    entry = """        <dict>\n            <key>CFBundleTypeRole</key>\n            <string>Viewer</string>\n            <key>CFBundleURLName</key>\n            <string>{telegram_bundle_id}.jerkgram</string>\n            <key>CFBundleURLSchemes</key>\n            <array>\n                <string>jerkgram</string>\n            </array>\n        </dict>\n"""
    path.write_text(text.replace(anchor, entry + anchor, 1))


def patch_app_delegate(path: Path) -> None:
    text = path.read_text()
    marker = "private func handleJerkgramPushUrl(_ url: URL) -> Bool"
    open_anchor = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {\n        self.openUrl(url: url)\n        return true\n    }\n"""

    helper = r'''    // MARK: Jerkgram Push Companion click bridge
    private func handleJerkgramPushUrl(_ url: URL) -> Bool {
        guard url.scheme?.lowercased() == "jerkgram" else {
            return false
        }

        // The scheme belongs to Jerkgram. Consume malformed Jerkgram URLs here
        // rather than forwarding them into Telegram's normal URL parser.
        guard url.absoluteString.utf8.count <= 1024,
              url.host?.lowercased() == "push",
              url.path == "/open",
              let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            return true
        }

        var values: [String: String] = [:]
        for item in components.queryItems ?? [] {
            if values[item.name] == nil, let value = item.value {
                values[item.name] = value
            }
        }

        func positiveInt64(_ key: String) -> Int64? {
            guard let raw = values[key], !raw.isEmpty, raw.count <= 20,
                  raw.allSatisfy({ $0 >= "0" && $0 <= "9" }),
                  let value = Int64(raw), value > 0 else {
                return nil
            }
            return value
        }

        guard let kind = values["kind"],
              let peerValue = positiveInt64("peer") else {
            return true
        }

        let peerId: PeerId
        switch kind {
        case "user":
            peerId = PeerId(namespace: Namespaces.Peer.CloudUser, id: PeerId.Id._internalFromInt64Value(peerValue))
        case "chat":
            peerId = PeerId(namespace: Namespaces.Peer.CloudGroup, id: PeerId.Id._internalFromInt64Value(peerValue))
        case "channel":
            peerId = PeerId(namespace: Namespaces.Peer.CloudChannel, id: PeerId.Id._internalFromInt64Value(peerValue))
        default:
            return true
        }

        var messageId: MessageId?
        if let rawMessageId = positiveInt64("msg") {
            guard rawMessageId <= Int64(Int32.max) else {
                return true
            }
            messageId = MessageId(peerId: peerId, namespace: Namespaces.Message.Cloud, id: Int32(rawMessageId))
        }

        var threadId: Int64?
        if let rawThreadId = positiveInt64("thread") {
            guard rawThreadId <= Int64(Int32.max) else {
                return true
            }
            threadId = rawThreadId
        }

        let targetUserId = positiveInt64("user")
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

                var targetAccountId: AccountRecordId?
                if let targetUserId = targetUserId {
                    for (recordId, context, _) in activeAccounts.accounts {
                        if context.account.peerId.id._internalGetInt64Value() == targetUserId {
                            targetAccountId = recordId
                            break
                        }
                    }
                    // Never open a notification in the wrong logged-in account.
                    guard targetAccountId != nil else {
                        return
                    }
                }

                self.openChatWhenReady(
                    accountId: targetAccountId,
                    peerId: peerId,
                    threadId: threadId,
                    messageId: messageId,
                    storyId: nil,
                    alwaysKeepMessageId: true
                )
            })
        })
        return true
    }

'''

    if marker not in text:
        if open_anchor not in text:
            raise SystemExit("[jerkgram-push-click] AppDelegate open-url anchor not found")
        text = text.replace(open_anchor, helper + open_anchor, 1)

    patched_open = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {\n        if self.handleJerkgramPushUrl(url) {\n            return true\n        }\n        self.openUrl(url: url)\n        return true\n    }\n"""
    if patched_open not in text:
        if open_anchor not in text:
            raise SystemExit("[jerkgram-push-click] AppDelegate dispatch anchor not found")
        text = text.replace(open_anchor, patched_open, 1)

    path.write_text(text)


patch_plist(INFO_BAZEL)
patch_plist(INFO_PLIST)
patch_build(BUILD)
patch_app_delegate(APP_DELEGATE)

print("[jerkgram-push-click] OK")
print("  patched:", APP_DELEGATE)
print("  patched:", INFO_BAZEL)
print("  patched:", INFO_PLIST)
print("  patched:", BUILD)
