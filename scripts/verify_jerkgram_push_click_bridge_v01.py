#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
paths = {
    "app": ROOT / "submodules/TelegramUI/Sources/AppDelegate.swift",
    "info_bazel": ROOT / "Telegram/Telegram-iOS/InfoBazel.plist",
    "info": ROOT / "Telegram/Telegram-iOS/Info.plist",
    "build": ROOT / "Telegram/BUILD",
    "register": ROOT / "submodules/TelegramCore/Sources/TelegramEngine/AccountData/RegisterNotificationToken.swift",
}

errors = []
for name, path in paths.items():
    if not path.exists():
        errors.append(f"missing {name}: {path}")

if errors:
    print("[jerkgram-push-click-verify] FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

app = paths["app"].read_text()
for marker in (
    "private func handleJerkgramPushUrl(_ url: URL) -> Bool",
    'url.scheme?.lowercased() == "jerkgram"',
    'url.host?.lowercased() == "push"',
    'case "user":',
    "Namespaces.Peer.CloudUser",
    'case "chat":',
    "Namespaces.Peer.CloudGroup",
    'case "channel":',
    "Namespaces.Peer.CloudChannel",
    "self.openChatWhenReady(",
    "alwaysKeepMessageId: true",
    "if self.handleJerkgramPushUrl(url)",
):
    if marker not in app:
        errors.append(f"AppDelegate missing marker: {marker}")

if app.count("private func handleJerkgramPushUrl(_ url: URL) -> Bool") != 1:
    errors.append("AppDelegate Jerkgram handler must exist exactly once")

for name in ("info_bazel", "info", "build"):
    text = paths[name].read_text()
    if text.count("<string>jerkgram</string>") != 1:
        errors.append(f"{name}: jerkgram URL scheme must exist exactly once")
    if "<string>telegram</string>" not in text:
        errors.append(f"{name}: existing telegram URL scheme disappeared")
    if "<string>tg</string>" not in text:
        errors.append(f"{name}: existing tg URL scheme disappeared")

register = paths["register"].read_text()
if "mappedType = 1" not in register:
    errors.append("RegisterNotificationToken: APNs token type 1 mapping disappeared")
if "mappedType = 9" not in register:
    errors.append("RegisterNotificationToken: VoIP token type 9 mapping disappeared")

if errors:
    print("[jerkgram-push-click-verify] FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("[jerkgram-push-click-verify] PASS")
