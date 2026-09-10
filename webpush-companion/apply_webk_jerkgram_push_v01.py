#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
PUSH = ROOT / "src/lib/serviceWorker/push.ts"
PUBLIC = ROOT / "public"
HERE = Path(__file__).resolve().parent

if not PUSH.exists():
    raise SystemExit(f"[jerkgram-webk] missing {PUSH}")

source = PUSH.read_text()
import_line = "import {buildJerkgramLandingUrl} from '@lib/serviceWorker/jerkgramPushHandoff';"
import_anchor = "import {getWindowClients} from '@helpers/context';"

if import_line not in source:
    if import_anchor not in source:
        raise SystemExit("[jerkgram-webk] import anchor not found")
    source = source.replace(import_anchor, import_anchor + "\n" + import_line, 1)

click_anchor = """  const data: PushNotificationObject = notification.data;\n  if(!data) {\n    return;\n  }\n"""
click_injection = click_anchor + """\n  // Jerkgram: default notification taps leave the web companion and open the\n  // exact account/chat/message in the native client. Keep action buttons in\n  // Telegram Web K's existing handler.\n  if(!action && ctx.clients.openWindow) {\n    const handoffUrl = buildJerkgramLandingUrl(ctx.registration.scope, data);\n    if(handoffUrl) {\n      event.waitUntil(ctx.clients.openWindow(handoffUrl));\n      return;\n    }\n  }\n"""

marker = "// Jerkgram: default notification taps leave the web companion"
if marker not in source:
    if click_anchor not in source:
        raise SystemExit("[jerkgram-webk] notification-click anchor not found")
    source = source.replace(click_anchor, click_injection, 1)

PUSH.write_text(source)

helper = (HERE / "handoff.js").read_text()
(ROOT / "src/lib/serviceWorker/jerkgramPushHandoff.ts").write_text(helper)
PUBLIC.mkdir(parents=True, exist_ok=True)
shutil.copyfile(HERE / "handoff.js", PUBLIC / "handoff.js")
shutil.copyfile(HERE / "open.html", PUBLIC / "open.html")

print("[jerkgram-webk] OK")
print("  patched:", PUSH)
print("  created: src/lib/serviceWorker/jerkgramPushHandoff.ts")
print("  created: public/handoff.js")
print("  created: public/open.html")
