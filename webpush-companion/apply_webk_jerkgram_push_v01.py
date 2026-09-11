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
import_handoff = "import {buildJerkgramLandingUrl} from '@lib/serviceWorker/jerkgramPushHandoff';"
import_presentation = "import {buildJerkgramPushPresentation} from '@lib/serviceWorker/jerkgramPushPresentation';"
import_anchor = "import {getWindowClients} from '@helpers/context';"

if import_handoff not in source:
    if import_anchor not in source:
        raise SystemExit("[jerkgram-webk] import anchor not found")
    source = source.replace(import_anchor, import_anchor + "\n" + import_handoff, 1)

if import_presentation not in source:
    if import_handoff not in source:
        raise SystemExit("[jerkgram-webk] handoff import missing before presentation import")
    source = source.replace(import_handoff, import_handoff + "\n" + import_presentation, 1)

click_anchor = """  const data: PushNotificationObject = notification.data;\n  if(!data) {\n    return;\n  }\n"""
click_injection = click_anchor + """\n  // Jerkgram: default notification taps leave the web companion and open the\n  // exact account/chat/message in the native client. Keep action buttons in\n  // Telegram Web K's existing handler.\n  if(!action && ctx.clients.openWindow) {\n    const handoffUrl = buildJerkgramLandingUrl(ctx.registration.scope, data);\n    if(handoffUrl) {\n      event.waitUntil(ctx.clients.openWindow(handoffUrl));\n      return;\n    }\n  }\n"""

click_marker = "// Jerkgram: default notification taps leave the web companion"
if click_marker not in source:
    if click_anchor not in source:
        raise SystemExit("[jerkgram-webk] notification-click anchor not found")
    source = source.replace(click_anchor, click_injection, 1)

presentation_anchor = """  let title = obj.title || 'Telegram';\n  let body = obj.description || '';\n  let tag = 'peer' + peerId;\n"""
presentation_injection = presentation_anchor + """\n  // Telegram's loc_key/loc_args carry the actual sender/chat/message text.\n  // Prefer those for visible previews; the stock no-preview branch below still\n  // overrides this completely when notification previews are disabled.\n  const jerkgramPresentation = buildJerkgramPushPresentation(obj);\n  title = jerkgramPresentation.title;\n  body = jerkgramPresentation.body;\n"""

presentation_marker = "const jerkgramPresentation = buildJerkgramPushPresentation(obj);"
if presentation_marker not in source:
    if presentation_anchor not in source:
        raise SystemExit("[jerkgram-webk] notification presentation anchor not found")
    source = source.replace(presentation_anchor, presentation_injection, 1)

for invariant in (
    import_handoff,
    import_presentation,
    click_marker,
    presentation_marker,
    "title = jerkgramPresentation.title;",
    "body = jerkgramPresentation.body;",
):
    if invariant not in source:
        raise SystemExit(f"[jerkgram-webk] invariant missing after patch: {invariant}")

PUSH.write_text(source)

handoff_helper = (HERE / "handoff.js").read_text()
presentation_helper = (HERE / "presentation.js").read_text()
(ROOT / "src/lib/serviceWorker/jerkgramPushHandoff.ts").write_text(handoff_helper)
(ROOT / "src/lib/serviceWorker/jerkgramPushPresentation.ts").write_text(presentation_helper)
PUBLIC.mkdir(parents=True, exist_ok=True)
shutil.copyfile(HERE / "handoff.js", PUBLIC / "handoff.js")
shutil.copyfile(HERE / "open.html", PUBLIC / "open.html")

print("[jerkgram-webk] OK")
print("  patched:", PUSH)
print("  created: src/lib/serviceWorker/jerkgramPushHandoff.ts")
print("  created: src/lib/serviceWorker/jerkgramPushPresentation.ts")
print("  created: public/handoff.js")
print("  created: public/open.html")
