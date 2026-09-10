from pathlib import Path
import subprocess
import sys


def make_fixture(root: Path):
    (root / "src/pages/cards").mkdir(parents=True)
    (root / "src/pages").mkdir(parents=True, exist_ok=True)
    (root / "src/lib").mkdir(parents=True)

    (root / "src/pages/mountAuthFlow.tsx").write_text("""function authStateToCardSpec(authState) {\n  switch(authState._) {\n    case 'authStateSignIn':\n      return {name: 'signIn'};\n    case 'authStateSignQr':\n      return {name: 'signQR'};\n  }\n}\n""")

    (root / "src/pages/cards/SignQRCard.tsx").write_text("""import LanguageChangeButton from '@components/languageChangeButton';\nimport PasskeyLoginButton from '@components/passkeyLoginButton';\nimport {getCurrentAccount} from '@lib/accounts/getCurrentAccount';\n// auth.exportLoginToken\n// jerkgram://push/authorize\n// toIm()\nexport default function SignQRCard(_props: {spec: any}) {\n  const {navigate} = useAuthFlow();\n  const helpList = (<ol><li>QR help</li></ol>);\n  return (\n    <AuthCard>\n      {helpList}\n      <Button>Connect with Jerkgram</Button>\n      <Button onClick={() => navigate({name: 'signIn'})}>Cancel</Button>\n      {getCurrentAccount() === 1 && <LanguageChangeButton />}\n      <PasskeyLoginButton />\n    </AuthCard>\n  );\n}\n""")

    (root / "src/pages/bootstrapIm.ts").write_text("""import rootScope from '@lib/rootScope';\nimport {disposeActiveAuthFlow} from '@/pages/mountAuthFlow';\nexport async function bootstrapIm(): Promise<void> {\n  await rootScope.managers.appStateManager.pushToState('authState', {_: 'authStateSignedIn'});\n  const [{default: appDialogsManager}] = await Promise.all([import('@lib/appDialogsManager')]);\n  appDialogsManager.start();\n  disposeActiveAuthFlow();\n}\n""")

    (root / "src/lib/appImManager.ts").write_text("""import uiNotificationsManager from '@lib/uiNotificationsManager';\nexport class AppImManager {\n  public construct(managers: any) {\n    this.managers = managers;\n    uiNotificationsManager.constructAndStartAll();\n    mountJerkgramCompanionShell();\n  }\n}\n""")


def test_companion_uses_notification_only_bootstrap(tmp_path: Path):
    root = tmp_path / "tweb"
    make_fixture(root)
    patcher = Path(__file__).parents[1] / "webpush-companion/apply_webk_jerkgram_minimal_ui_v01.py"
    result = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout

    auth = (root / "src/pages/mountAuthFlow.tsx").read_text()
    assert "case 'authStateSignIn':\n      return {name: 'signQR'};" in auth

    qr = (root / "src/pages/cards/SignQRCard.tsx").read_text()
    assert "Connect with Jerkgram" in qr
    assert "auth.exportLoginToken" in qr
    assert "jerkgram://push/authorize" in qr
    assert "LanguageChangeButton" not in qr
    assert "PasskeyLoginButton" not in qr
    assert "{helpList}" not in qr
    assert "navigate({name: 'signIn'})" not in qr

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

    push = (root / "src/lib/jerkgramCompanionPush.ts").read_text()
    assert "webPushApiManager.subscribe()" in push
    assert "apiManagerProxy.pushSingleManager.registerDevice(tokenData)" in push
    assert "SETTINGS_INIT.notifications" in push

    app_im = (root / "src/lib/appImManager.ts").read_text()
    assert "mountJerkgramCompanionShell" not in app_im
