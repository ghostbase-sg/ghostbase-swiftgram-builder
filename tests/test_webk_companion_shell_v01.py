from pathlib import Path
import subprocess
import sys


def make_fixture(root: Path):
    (root / "src/pages/cards").mkdir(parents=True)
    (root / "src/pages").mkdir(parents=True, exist_ok=True)
    (root / "src/lib").mkdir(parents=True)

    (root / "src/pages/mountAuthFlow.tsx").write_text("""function authStateToCardSpec(authState) {\n  switch(authState._) {\n    case 'authStateSignIn':\n      return {name: 'signIn'};\n    case 'authStateSignQr':\n      return {name: 'signQR'};\n  }\n}\n""")

    (root / "src/pages/cards/SignQRCard.tsx").write_text("""import LanguageChangeButton from '@components/languageChangeButton';\nimport PasskeyLoginButton from '@components/passkeyLoginButton';\nimport {getCurrentAccount} from '@lib/accounts/getCurrentAccount';\n// auth.exportLoginToken\n// toIm()\nexport default function SignQRCard(_props: {spec: any}) {\n  const {navigate} = useAuthFlow();\n  let lastDrawnToken: Uint8Array | number[] | undefined;\n  function connectWithJerkgram() {\n    window.location.assign('jerkgram://push/authorize?token=' + encodeURIComponent('token'));\n  }\n  const helpList = (<ol><li>QR help</li></ol>);\n  return (\n    <AuthCard>\n      {helpList}\n      {/* Jerkgram Push Companion primary pairing action */}\n      <Button primaryFilled large onClick={connectWithJerkgram}>Connect with Jerkgram</Button>\n      <Button onClick={() => navigate({name: 'signIn'})}>Cancel</Button>\n      {getCurrentAccount() === 1 && <LanguageChangeButton />}\n      <PasskeyLoginButton />\n    </AuthCard>\n  );\n}\n""")

    (root / "src/lib/appImManager.ts").write_text("""import uiNotificationsManager from '@lib/uiNotificationsManager';\nexport class AppImManager {\n  public construct(managers: any) {\n    this.managers = managers;\n    uiNotificationsManager.constructAndStartAll();\n    appMediaPlaybackController.construct(managers);\n  }\n}\n""")


def test_companion_shell_patch(tmp_path: Path):
    root = tmp_path / "tweb"
    make_fixture(root)
    patcher = Path(__file__).parents[1] / "webpush-companion/apply_webk_jerkgram_minimal_ui_v01.py"
    result = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout

    auth = (root / "src/pages/mountAuthFlow.tsx").read_text()
    assert "case 'authStateSignIn':\n      return {name: 'signQR'};" in auth

    qr = (root / "src/pages/cards/SignQRCard.tsx").read_text()
    assert "Connect with Jerkgram" in qr
    assert "LanguageChangeButton" not in qr
    assert "PasskeyLoginButton" not in qr
    assert "{helpList}" not in qr
    assert "navigate({name: 'signIn'})" not in qr

    im = (root / "src/lib/appImManager.ts").read_text()
    assert "import mountJerkgramCompanionShell from '@lib/jerkgramCompanionShell';" in im
    assert "mountJerkgramCompanionShell();" in im

    shell = (root / "src/lib/jerkgramCompanionShell.ts").read_text()
    assert "Notification.requestPermission()" in shell
    assert "uiNotificationsManager.onPushConditionsChange()" in shell
    assert "matchMedia('(display-mode: standalone)')" in shell
    assert "innerHTML" not in shell
    assert "Jerkgram Notifications" in shell
