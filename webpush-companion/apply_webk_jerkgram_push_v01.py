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
import_tap = "import {buildJerkgramTapIdentity, normalizeJerkgramOpenUrl} from '@lib/serviceWorker/jerkgramTapFallback';"
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

if import_tap not in source:
    if import_presentation not in source:
        raise SystemExit("[jerkgram-webk] presentation import missing before tap import")
    source = source.replace(import_presentation, import_presentation + "\n" + import_tap, 1)

click_anchor = """  const data: PushNotificationObject = notification.data;\n  if(!data) {\n    return;\n  }\n"""
click_injection = click_anchor + """\n  // Jerkgram: default notification taps leave the web companion and open the\n  // exact account/chat/message in the native client. This is the first\n  // real-device-proven path: open the same-origin landing page directly and\n  // let open.html perform the validated jerkgram:// handoff.\n  if(!action && ctx.clients.openWindow) {\n    const handoffUrl = buildJerkgramLandingUrl(ctx.registration.scope, data);\n    if(handoffUrl) {\n      event.waitUntil(ctx.clients.openWindow(handoffUrl));\n      return;\n    }\n  }\n"""

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

persist_marker = "async function persistJerkgramTapState(obj: PushNotificationObject)"
if persist_marker not in source:
    fire_anchor = "function fireNotification(\n"
    if fire_anchor not in source:
        raise SystemExit("[jerkgram-webk] fireNotification anchor not found")

    persist_helper = r'''const JERKGRAM_TAP_CACHE = 'jerkgram-push-tap-v1';
const JERKGRAM_TAP_SNAPSHOT_NAME = '__jerkgram_tap_snapshot__';
const JERKGRAM_TAP_RECORD_PREFIX = '__jerkgram_tap_record__/';
const JERKGRAM_TAP_TTL_MS = 6 * 60 * 60 * 1000;

async function persistJerkgramTapState(obj: PushNotificationObject) {
  const id = buildJerkgramTapIdentity(obj);
  const nativeUrl = normalizeJerkgramOpenUrl(buildJerkgramNativeUrlFromPush(obj));
  if(!id || !nativeUrl) return;

  try {
    const cache = await ctx.caches.open(JERKGRAM_TAP_CACHE);
    const expiresAt = Date.now() + JERKGRAM_TAP_TTL_MS;
    const recordKey = new URL(JERKGRAM_TAP_RECORD_PREFIX + encodeURIComponent(id), ctx.registration.scope).href;
    await cache.put(recordKey, new Response(JSON.stringify({id, url: nativeUrl, expiresAt}), {
      headers: {'content-type': 'application/json', 'cache-control': 'no-store'}
    }));

    const liveNotifications = await ctx.registration.getNotifications();
    const ids = [...new Set(liveNotifications
      .map((notification) => buildJerkgramTapIdentity(notification.data))
      .filter(Boolean))];
    const snapshotKey = new URL(JERKGRAM_TAP_SNAPSHOT_NAME, ctx.registration.scope).href;
    await cache.put(snapshotKey, new Response(JSON.stringify({ids, savedAt: Date.now()}), {
      headers: {'content-type': 'application/json', 'cache-control': 'no-store'}
    }));

    const requests = await cache.keys();
    for(const request of requests) {
      if(!request.url.includes(JERKGRAM_TAP_RECORD_PREFIX)) continue;
      const response = await cache.match(request);
      if(!response) continue;
      try {
        const record = await response.json();
        if(!record || typeof record.expiresAt !== 'number' || record.expiresAt <= Date.now()) {
          await cache.delete(request);
        }
      } catch(_) {
        await cache.delete(request);
      }
    }
  } catch(_) {
    // Tap fallback is best-effort; notification delivery must never depend on it.
  }
}

'''
    source = source.replace(fire_anchor, persist_helper + fire_anchor, 1)

persist_call = "  void notificationPromise.then(() => persistJerkgramTapState(obj));"
if persist_call not in source:
    promise_anchor = "  const notificationPromise = ctx.registration.showNotification(title, notificationOptions);"
    direct_anchor = "  return ctx.registration.showNotification(title, notificationOptions);"
    if promise_anchor in source:
        source = source.replace(promise_anchor, promise_anchor + "\n" + persist_call, 1)
    elif direct_anchor in source:
        replacement = (
            "  const notificationPromise = ctx.registration.showNotification(title, notificationOptions);\n"
            + persist_call
            + "\n  return notificationPromise;"
        )
        source = source.replace(direct_anchor, replacement, 1)
    else:
        raise SystemExit("[jerkgram-webk] showNotification anchor not found")

for invariant in (
    import_handoff,
    import_presentation,
    import_tap,
    click_marker,
    "event.waitUntil(ctx.clients.openWindow(handoffUrl));",
    presentation_marker,
    "title = jerkgramPresentation.title;",
    "body = jerkgramPresentation.body;",
    persist_marker,
    "jerkgram-push-tap-v1",
    "ctx.registration.getNotifications()",
    "JSON.stringify({id, url: nativeUrl, expiresAt})",
    persist_call,
):
    if invariant not in source:
        raise SystemExit(f"[jerkgram-webk] invariant missing after patch: {invariant}")

for forbidden in (
    "jerkgramNavigateUrl",
    "NotificationOptions & {navigate?: string}",
    ".navigate(handoffUrl)",
    "ctx.clients.matchAll({type: 'window', includeUncontrolled: true})",
    "jerkgram-push-handoff-v1",
):
    if forbidden in source:
        raise SystemExit(f"[jerkgram-webk] legacy click workaround still present: {forbidden}")

PUSH.write_text(source)

html = INDEX.read_text()
resolver_tag = '  <script src="./push-tap-resolver.js"></script>\n'
if resolver_tag not in html:
    if "</head>" not in html:
        raise SystemExit("[jerkgram-webk] index </head> anchor not found")
    html = html.replace("</head>", resolver_tag + "</head>", 1)
if "push-open-bootstrap.js" in html:
    raise SystemExit("[jerkgram-webk] legacy push-open bootstrap still referenced")
INDEX.write_text(html)

handoff_helper = (HERE / "handoff.js").read_text()
presentation_helper = (HERE / "presentation.js").read_text()
tap_helper = (HERE / "tap-fallback.js").read_text()
(ROOT / "src/lib/serviceWorker/jerkgramPushHandoff.ts").write_text(handoff_helper)
(ROOT / "src/lib/serviceWorker/jerkgramPushPresentation.ts").write_text(presentation_helper)
(ROOT / "src/lib/serviceWorker/jerkgramTapFallback.ts").write_text(tap_helper)
PUBLIC.mkdir(parents=True, exist_ok=True)
shutil.copyfile(HERE / "handoff.js", PUBLIC / "handoff.js")
shutil.copyfile(HERE / "tap-fallback.js", PUBLIC / "tap-fallback.js")
shutil.copyfile(HERE / "open.html", PUBLIC / "open.html")
shutil.copyfile(HERE / "push-tap-resolver.js", PUBLIC / "push-tap-resolver.js")

print("[jerkgram-webk] OK")
print("  patched:", PUSH)
print("  patched:", INDEX)
print("  created: src/lib/serviceWorker/jerkgramPushHandoff.ts")
print("  created: src/lib/serviceWorker/jerkgramPushPresentation.ts")
print("  created: src/lib/serviceWorker/jerkgramTapFallback.ts")
print("  created: public/handoff.js")
print("  created: public/tap-fallback.js")
print("  created: public/open.html")
print("  created: public/push-tap-resolver.js")
