#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
PUSH = ROOT / "src/lib/serviceWorker/push.ts"
INDEX = ROOT / "index.html"
PUBLIC = ROOT / "public"
HERE = Path(__file__).resolve().parent

if not PUSH.exists() or not INDEX.exists():
    raise SystemExit(f"[jerkgram-webk] missing required Web K files under {ROOT}")

source = PUSH.read_text()
import_handoff = "import {buildJerkgramLandingUrl, buildJerkgramNativeUrlFromPush} from '@lib/serviceWorker/jerkgramPushHandoff';"
old_import_handoff = "import {buildJerkgramLandingUrl} from '@lib/serviceWorker/jerkgramPushHandoff';"
import_presentation = "import {buildJerkgramPushPresentation} from '@lib/serviceWorker/jerkgramPushPresentation';"
import_anchor = "import {getWindowClients} from '@helpers/context';"

if old_import_handoff in source:
    source = source.replace(old_import_handoff, import_handoff, 1)
elif import_handoff not in source:
    if import_anchor not in source:
        raise SystemExit("[jerkgram-webk] import anchor not found")
    source = source.replace(import_anchor, import_anchor + "\n" + import_handoff, 1)

if import_presentation not in source:
    if import_handoff not in source:
        raise SystemExit("[jerkgram-webk] handoff import missing before presentation import")
    source = source.replace(import_handoff, import_handoff + "\n" + import_presentation, 1)

click_anchor = """  const data: PushNotificationObject = notification.data;\n  if(!data) {\n    return;\n  }\n"""
click_injection = click_anchor + """\n  // Jerkgram: default notification taps leave the web companion and open the\n  // exact account/chat/message in the native client. iOS/WebKit can cold-launch\n  // a Home Screen PWA at its start_url instead of the URL passed to openWindow,\n  // so persist the native handoff and also navigate any existing PWA client.\n  if(!action && ctx.clients.openWindow) {\n    const landing = buildJerkgramLandingUrl(ctx.registration.scope, data);\n    const nativeUrl = buildJerkgramNativeUrlFromPush(data);\n    if(landing && nativeUrl) {\n      const landingUrl = new URL(landing);\n      landingUrl.searchParams.set('_jg', Date.now().toString());\n      const handoffUrl = landingUrl.href;\n\n      event.waitUntil((async() => {\n        const pendingKey = new URL('__jerkgram_pending_push__', ctx.registration.scope).href;\n        try {\n          const cache = await ctx.caches.open('jerkgram-push-handoff-v1');\n          await cache.put(pendingKey, new Response(JSON.stringify({\n            url: nativeUrl,\n            expiresAt: Date.now() + 30000\n          }), {headers: {'content-type': 'application/json'}}));\n        } catch(_) {\n          // The same-origin landing page remains a functional fallback.\n        }\n\n        const windowClients = await ctx.clients.matchAll({type: 'window', includeUncontrolled: true});\n        for(const client of windowClients) {\n          try {\n            const navigated = await client.navigate(handoffUrl);\n            await (navigated || client).focus();\n            return;\n          } catch(_) {\n            // Continue to openWindow fallback below.\n          }\n        }\n\n        await ctx.clients.openWindow(handoffUrl);\n      })());\n      return;\n    }\n  }\n"""

click_marker = "// Jerkgram: default notification taps leave the web companion"
if click_marker not in source:
    if click_anchor not in source:
        raise SystemExit("[jerkgram-webk] notification-click anchor not found")
    source = source.replace(click_anchor, click_injection, 1)
else:
    # Replace the older one-shot openWindow branch with the iOS-safe variant.
    branch_start = source.index("  // Jerkgram: default notification taps leave the web companion")
    branch_end_marker = "\n  const promise = Promise.all(["
    if branch_end_marker in source[branch_start:]:
        branch_end = source.index(branch_end_marker, branch_start)
        source = source[:branch_start] + click_injection[len(click_anchor):] + source[branch_end:]

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
    "buildJerkgramNativeUrlFromPush",
    "jerkgram-push-handoff-v1",
    "ctx.clients.matchAll({type: 'window', includeUncontrolled: true})",
    ".navigate(handoffUrl)",
    "ctx.clients.openWindow(handoffUrl)",
    presentation_marker,
    "title = jerkgramPresentation.title;",
    "body = jerkgramPresentation.body;",
):
    if invariant not in source:
        raise SystemExit(f"[jerkgram-webk] invariant missing after patch: {invariant}")

PUSH.write_text(source)

html = INDEX.read_text()
bootstrap_tag = '  <script src="./push-open-bootstrap.js"></script>\n'
if bootstrap_tag not in html:
    if "</head>" not in html:
        raise SystemExit("[jerkgram-webk] index </head> anchor not found")
    html = html.replace("</head>", bootstrap_tag + "</head>", 1)
INDEX.write_text(html)

handoff_helper = (HERE / "handoff.js").read_text()
presentation_helper = (HERE / "presentation.js").read_text()
(ROOT / "src/lib/serviceWorker/jerkgramPushHandoff.ts").write_text(handoff_helper)
(ROOT / "src/lib/serviceWorker/jerkgramPushPresentation.ts").write_text(presentation_helper)
PUBLIC.mkdir(parents=True, exist_ok=True)
shutil.copyfile(HERE / "handoff.js", PUBLIC / "handoff.js")
shutil.copyfile(HERE / "open.html", PUBLIC / "open.html")
shutil.copyfile(HERE / "push-open-bootstrap.js", PUBLIC / "push-open-bootstrap.js")

print("[jerkgram-webk] OK")
print("  patched:", PUSH)
print("  patched:", INDEX)
print("  created: src/lib/serviceWorker/jerkgramPushHandoff.ts")
print("  created: src/lib/serviceWorker/jerkgramPushPresentation.ts")
print("  created: public/handoff.js")
print("  created: public/open.html")
print("  created: public/push-open-bootstrap.js")
