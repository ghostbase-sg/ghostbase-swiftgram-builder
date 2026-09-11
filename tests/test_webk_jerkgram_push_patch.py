from pathlib import Path
import subprocess
import sys


def test_webk_push_patch(tmp_path: Path):
    root = tmp_path / "tweb"
    target = root / "src/lib/serviceWorker/push.ts"
    service_index = root / "src/lib/serviceWorker/index.service.ts"
    target.parent.mkdir(parents=True)
    (root / "public").mkdir()
    (root / "index.html").write_text("<html><head></head><body></body></html>")
    service_original = (
        "const ctx = self as any as ServiceWorkerGlobalScope;\n"
        "const onFetch = (event: FetchEvent): void => {\n"
        "  EXISTING_FETCH_HANDLER();\n"
        "};\n"
    )
    service_index.write_text(service_original)
    target.write_text(
        "import {getWindowClients} from '@helpers/context';\n\n"
        "function onNotificationClick(event: NotificationEvent) {\n"
        "  const notification = event.notification;\n"
        "  notification.close();\n"
        "  const action = event.action as PushNotificationObject['action'];\n"
        "  const data: PushNotificationObject = notification.data;\n"
        "  if(!data) {\n"
        "    return;\n"
        "  }\n"
        "  EXISTING_WEBK_HANDLER();\n"
        "}\n\n"
        "function fireNotification(\n"
        "  obj: PushNotificationObject,\n"
        "  settings: PushStorage['push_settings'],\n"
        "  lang: PushStorage['push_lang']\n"
        ") {\n"
        "  obj = fillPushObject(obj);\n"
        "  const peerId = obj.custom.peerId;\n"
        "  let title = obj.title || 'Telegram';\n"
        "  let body = obj.description || '';\n"
        "  let tag = 'peer' + peerId;\n\n"
        "  if(settings?.nopreview || !obj.loc_key) {\n"
        "    title = 'Telegram';\n"
        "    body = lang.push_message_nopreview;\n"
        "    tag = 'unknown_peer';\n"
        "  }\n\n"
        "  const notificationOptions: NotificationOptions = {\n"
        "    body,\n"
        "    icon: NOTIFICATION_ICON_PATH,\n"
        "    tag,\n"
        "    data: obj,\n"
        "    actions: [],\n"
        "    badge: NOTIFICATION_BADGE_PATH,\n"
        "    silent: obj.custom.silent === '1'\n"
        "  };\n\n"
        "  return ctx.registration.showNotification(title, notificationOptions);\n"
        "}\n"
    )

    patcher = Path(__file__).parents[1] / "webpush-companion/apply_webk_jerkgram_push_v01.py"
    result = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout

    patched = target.read_text()
    assert "buildJerkgramLandingUrl" in patched
    assert "EXISTING_WEBK_HANDLER();" in patched
    assert patched.count("Jerkgram: default notification taps") == 1
    assert (root / "src/lib/serviceWorker/jerkgramPushHandoff.ts").exists()
    assert (root / "src/lib/serviceWorker/jerkgramPushPresentation.ts").exists()
    assert (root / "src/lib/serviceWorker/jerkgramTapFallback.ts").exists()
    assert (root / "public/handoff.js").exists()
    assert (root / "public/tap-fallback.js").exists()
    assert (root / "public/open.html").exists()
    assert (root / "public/push-tap-resolver.js").exists()

    # Restore the first real-device-proven click path: notificationclick opens
    # same-origin open.html directly; open.html performs the custom-scheme jump.
    assert "event.waitUntil(ctx.clients.openWindow(handoffUrl));" in patched
    assert "ctx.clients.matchAll({type: 'window', includeUncontrolled: true})" not in patched
    assert ".navigate(handoffUrl)" not in patched
    assert "jerkgramNavigateUrl" not in patched
    assert "NotificationOptions & {navigate?: string}" not in patched

    # Do not intercept Web K navigation requests anymore. That later workaround
    # was introduced after the working build and regressed real-device taps.
    assert service_index.read_text() == service_original
    assert "tryJerkgramPendingNavigation" not in service_index.read_text()

    # After a notification is shown, persist only routing metadata and a snapshot
    # of live notification identities for the root-screen WebKit fallback.
    assert "persistJerkgramTapState" in patched
    assert "jerkgram-push-tap-v1" in patched
    assert "ctx.registration.getNotifications()" in patched
    assert "buildJerkgramTapIdentity" in patched
    assert "normalizeJerkgramOpenUrl" in patched
    assert "JSON.stringify({id, url: nativeUrl, expiresAt})" in patched

    html = (root / "index.html").read_text()
    assert '<script src="./push-tap-resolver.js"></script>' in html
    assert 'type="module" src="./push-tap-resolver.js"' not in html
    assert "push-open-bootstrap.js" not in html

    # The resolver is a public classic script so Vite does not attempt to bundle
    # it from the project root. It loads the public helper lazily at runtime.
    resolver = (root / "public/push-tap-resolver.js").read_text()
    assert "import('./tap-fallback.js')" in resolver
    assert not resolver.lstrip().startswith("import {")

    # Visible notification presentation remains independent of tap routing.
    assert "buildJerkgramPushPresentation" in patched
    assert "const jerkgramPresentation = buildJerkgramPushPresentation(obj);" in patched
    assert "title = jerkgramPresentation.title;" in patched
    assert "body = jerkgramPresentation.body;" in patched
    assert "if(settings?.nopreview || !obj.loc_key)" in patched

    # Idempotent: a second patch must not duplicate branches or scripts.
    result2 = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert result2.returncode == 0, result2.stderr + result2.stdout
    patched2 = target.read_text()
    assert patched2.count("Jerkgram: default notification taps") == 1
    assert patched2.count("const jerkgramPresentation = buildJerkgramPushPresentation(obj);") == 1
    assert patched2.count("persistJerkgramTapState") >= 1
    assert (root / "index.html").read_text().count("push-tap-resolver.js") == 1
    assert service_index.read_text() == service_original
