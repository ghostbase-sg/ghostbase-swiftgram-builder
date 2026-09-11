from pathlib import Path
import subprocess
import sys


def test_webk_push_patch(tmp_path: Path):
    root = tmp_path / "tweb"
    target = root / "src/lib/serviceWorker/push.ts"
    target.parent.mkdir(parents=True)
    (root / "public").mkdir()
    (root / "index.html").write_text("<html><head></head><body></body></html>")
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
        "  }\n"
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
    assert (root / "public/handoff.js").exists()
    assert (root / "public/open.html").exists()

    # iOS/WebKit can cold-launch a Home Screen PWA at its start_url instead of
    # the URL passed to clients.openWindow(). Persist the native handoff and
    # actively navigate an existing client so notification taps cannot strand
    # the user on the companion root screen.
    assert "jerkgram-push-handoff-v1" in patched
    assert "buildJerkgramNativeUrlFromPush" in patched
    assert "ctx.clients.matchAll({type: 'window', includeUncontrolled: true})" in patched
    assert ".navigate(handoffUrl)" in patched
    assert "ctx.clients.openWindow(handoffUrl)" in patched
    assert (root / "public/push-open-bootstrap.js").exists()
    assert '<script src="./push-open-bootstrap.js"></script>' in (root / "index.html").read_text()

    # Visible notification presentation must use Telegram's loc_key/loc_args data
    # so private messages show sender + real message text instead of generic
    # "Telegram / sent you a message". Privacy/no-preview fallback stays stock.
    assert "buildJerkgramPushPresentation" in patched
    assert "const jerkgramPresentation = buildJerkgramPushPresentation(obj);" in patched
    assert "title = jerkgramPresentation.title;" in patched
    assert "body = jerkgramPresentation.body;" in patched
    assert "if(settings?.nopreview || !obj.loc_key)" in patched
    assert (root / "src/lib/serviceWorker/jerkgramPushPresentation.ts").exists()

    # Idempotent: a second patch must not duplicate the injected branches.
    result2 = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert result2.returncode == 0, result2.stderr + result2.stdout
    patched2 = target.read_text()
    assert patched2.count("Jerkgram: default notification taps") == 1
    assert patched2.count("const jerkgramPresentation = buildJerkgramPushPresentation(obj);") == 1
    assert (root / "index.html").read_text().count("push-open-bootstrap.js") == 1
