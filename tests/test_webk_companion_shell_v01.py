from pathlib import Path
import subprocess
import sys


def make_fixture(root: Path):
    (root / "src/pages/cards").mkdir(parents=True)
    (root / "src/pages").mkdir(parents=True, exist_ok=True)
    (root / "src/lib").mkdir(parents=True)

    (root / "src/pages/mountAuthFlow.tsx").write_text("""function authStateToCardSpec(authState) {\n  switch(authState._) {\n    case 'authStateSignIn':\n      return {name: 'signIn'};\n    case 'authStateSignQr':\n      return {name: 'signQR'};\n    case 'authStatePassword':\n      return {name: 'password'};\n  }\n}\n""")

    # This is intentionally a compact representation of the already-patched
    # SignQRCard. The minimal-UI layer may change presentation, but it must not
    # replace Web K's login-token protocol owner or its 2FA continuation.
    (root / "src/pages/cards/SignQRCard.tsx").write_text("""import Button from '@components/buttonTsx';\n// STOCK_QR_PROTOCOL_OWNER\n// auth.exportLoginToken\n// auth.importLoginToken\n// auth.loginTokenSuccess\n// SESSION_PASSWORD_NEEDED -> navigate({name: 'password'})\n// jerkgram://push/authorize\n// toIm()\nfunction isJerkgramStandalone(): boolean { return true; }\nexport default function SignQRCard(_props: {spec: any}) {\n  const {navigate} = useAuthFlow();\n  let stickerHost: HTMLDivElement;\n  const helpList = (<ol><li>QR help</li></ol>);\n  return (\n    <AuthCard>\n      {helpList}\n      {/* Jerkgram Push Companion primary pairing action */}\n      <Button onClick={connectWithJerkgram}>Connect with Jerkgram</Button>\n      <Button onClick={() => navigate({name: 'signIn'})}>Cancel</Button>\n    </AuthCard>\n  );\n}\n""")

    (root / "src/pages/bootstrapIm.ts").write_text("""import rootScope from '@lib/rootScope';\nimport {disposeActiveAuthFlow} from '@/pages/mountAuthFlow';\nexport async function bootstrapIm(): Promise<void> {\n  await rootScope.managers.appStateManager.pushToState('authState', {_: 'authStateSignedIn'});\n  const [{default: appDialogsManager}] = await Promise.all([import('@lib/appDialogsManager')]);\n  appDialogsManager.start();\n  disposeActiveAuthFlow();\n}\n""")

    (root / "src/lib/appImManager.ts").write_text("""import uiNotificationsManager from '@lib/uiNotificationsManager';\nexport class AppImManager {\n  public construct(managers: any) {\n    this.managers = managers;\n    uiNotificationsManager.constructAndStartAll();\n    mountJerkgramCompanionShell();\n  }\n}\n""")


def test_companion_uses_notification_only_bootstrap_without_reimplementing_qr_auth(tmp_path: Path):
    root = tmp_path / "tweb"
    make_fixture(root)
    patcher = Path(__file__).parents[1] / "webpush-companion/apply_webk_jerkgram_minimal_ui_v01.py"
    result = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout

    auth = (root / "src/pages/mountAuthFlow.tsx").read_text()
    assert "case 'authStateSignIn':\n      return {name: 'signQR'};" in auth
    assert "case 'authStatePassword':\n      return {name: 'password'};" in auth

    qr = (root / "src/pages/cards/SignQRCard.tsx").read_text()
    assert "STOCK_QR_PROTOCOL_OWNER" in qr
    assert "Connect with Jerkgram" in qr
    assert "auth.exportLoginToken" in qr
    assert "auth.importLoginToken" in qr
    assert "auth.loginTokenSuccess" in qr
    assert "SESSION_PASSWORD_NEEDED -> navigate({name: 'password'})" in qr
    assert "jerkgram://push/authorize" in qr
    assert "navigate({name: 'signIn'})" not in qr
    assert "disabled={!isJerkgramStandalone() || pairingBusy()}" in qr
    assert "Add Jerkgram Notifications to the Home Screen first." in qr
    assert "Open it from the Home Screen to connect." in qr

    bootstrap = (root / "src/pages/bootstrapIm.ts").read_text()
    assert "appDialogsManager" not in bootstrap
    assert "startJerkgramCompanionPushRuntime" in bootstrap
    assert "mountJerkgramCompanionShell" in bootstrap

    shell = (root / "src/lib/jerkgramCompanionShell.ts").read_text()
    assert "Notification.requestPermission()" in shell
    assert "ensureJerkgramPushRegistered()" in shell
    assert "matchMedia('(display-mode: standalone)')" in shell
    assert "uiNotificationsManager" not in shell
    assert "innerHTML" not in shell
    assert "Jerkgram Notifications" in shell
    assert "Connected as" in shell
    assert "Disconnect" in shell
    assert "apiManagerProxy.getUser(rootScope.myId.toUserId())" in shell
    assert "rootScope.managers.apiManager.logOut()" in shell

    push = (root / "src/lib/jerkgramCompanionPush.ts").read_text()
    assert "webPushApiManager.subscribe()" in push
    assert "apiManagerProxy.pushSingleManager.registerDevice(tokenData)" in push
    assert "apiManagerProxy.pushSingleManager.unregisterDevice(tokenData)" in push
    assert "webPushApiManager.unsubscribe()" in push
    assert "SETTINGS_INIT.notifications" in push

    app_im = (root / "src/lib/appImManager.ts").read_text()
    assert "mountJerkgramCompanionShell" not in app_im
