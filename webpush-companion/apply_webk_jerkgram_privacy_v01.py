#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
PUSH_MANAGER = ROOT / "src/lib/appManagers/pushSingleManager.ts"
SW_PUSH = ROOT / "src/lib/serviceWorker/push.ts"

if not PUSH_MANAGER.exists() or not SW_PUSH.exists():
    raise SystemExit("[jerkgram-webk-privacy] required Web K push files not found")


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise SystemExit(f"[jerkgram-webk-privacy] missing {label} anchor")


manager = PUSH_MANAGER.read_text()
manager = replace_required(
    manager,
    "this.log('register device', this.registeredDevice, tokenData, userIds);",
    "this.log('register device', {tokenType: tokenData.tokenType, accounts: userIds.length});",
    "registerDevice log",
)
manager = replace_required(
    manager,
    "this.log('unregister device', tokenData);",
    "this.log('unregister device', {tokenType: tokenData.tokenType});",
    "unregisterDevice log",
)
PUSH_MANAGER.write_text(manager)

push = SW_PUSH.read_text()
push = replace_required(push, "log('push', copy);", "log('push received');", "push payload log")
push = replace_required(
    push,
    "log.error('push notification error', err, copy);",
    "log.error('push notification error', err);",
    "push error payload log",
)
push = replace_required(push, "log('encrypted push', obj);", "log('encrypted push received');", "encrypted push payload log")
push = replace_required(
    push,
    "log('on notification click', notification);",
    "log('notification click');",
    "notification click payload log",
)
push = replace_required(
    push,
    "log('show notify', title, body, obj, notificationOptions);",
    "log('show notification');",
    "notification content log",
)
SW_PUSH.write_text(push)

print("[jerkgram-webk-privacy] OK")
