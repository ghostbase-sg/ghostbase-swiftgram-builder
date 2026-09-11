from pathlib import Path
import subprocess
import sys


def test_webk_pairing_patch_uses_fresh_token_and_safe_handoff(tmp_path: Path):
    root = tmp_path / "tweb"
    target = root / "src/pages/cards/SignQRCard.tsx"
    target.parent.mkdir(parents=True)
    target.write_text(
        "import {onCleanup, onMount} from 'solid-js';\n"
        "import Button from '@components/buttonTsx';\n"
        "import bytesToBase64 from '@helpers/bytes/bytesToBase64';\n"
        "import fixBase64String from '@helpers/fixBase64String';\n"
        "export default function SignQRCard() {\n"
        "  let stopped = false;\n"
        "  let prevToken: Uint8Array | undefined;\n"
        "  let lastDrawnToken: Uint8Array | number[] | undefined;\n"
        "  let QRCodeStylingCtor: any;\n"
        "  const helpList = null;\n"
        "  async function iterate(QRCodeStyling: any, isLoop: boolean): Promise<boolean> {\n"
        "    try {\n"
        "      const loginToken: any = {_: 'auth.loginToken', token: new Uint8Array([1])};\n"
        "      // auth.exportLoginToken / auth.importLoginToken / auth.loginTokenSuccess are owned by Web K.\n"
        "      if(!prevToken || !bytesCmp(prevToken, loginToken.token)) {\n"
        "        prevToken = loginToken.token;\n"
        "      }\n"
        "    } catch(err) {\n"
        "      switch((err as ApiError).type) {\n"
        "        case 'SESSION_PASSWORD_NEEDED':\n"
        "          navigate({name: 'password'});\n"
        "          stopped = true;\n"
        "          break;\n"
        "      }\n"
        "      return true;\n"
        "    }\n"
        "    return false;\n"
        "  }\n"
        "  return (<>\n"
        "      {helpList}\n"
        "      <Button\n"
        "        class=\"btn-primary btn-secondary btn-primary-transparent primary\"\n"
        "        onClick={() => {}}\n"
        "        text=\"Login.QR.Cancel\"\n"
        "      />\n"
        "  </>);\n"
        "}\n"
    )

    patcher = Path(__file__).parents[1] / "webpush-companion/apply_webk_jerkgram_pairing_v01.py"
    result = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout

    patched = target.read_text()
    assert "jerkgram://push/authorize?token=" in patched
    assert "Connect with Jerkgram" in patched
    assert "lastDrawnToken" in patched
    assert "bytesToBase64" in patched
    assert "fixBase64String" in patched

    # A tap must fetch a fresh token itself. Pairing must not depend on the hidden
    # QR renderer having already painted a token or loaded qr-code-styling.
    assert "async function connectWithJerkgram()" in patched
    assert "let freshToken: Uint8Array | number[] | undefined" in patched
    assert "onJerkgramToken?: (token: Uint8Array | number[]) => void" in patched
    assert "onJerkgramToken?.(loginToken.token)" in patched
    assert "if(!lastDrawnToken || !QRCodeStylingCtor)" not in patched
    assert "await iterate(undefined, false, (token) =>" in patched
    assert "freshToken = token" in patched
    assert "bytesToBase64(freshToken)" in patched
    assert "bytesToBase64(lastDrawnToken)" not in patched

    # Pairing must happen inside the installed Home Screen web app. Safari and the
    # web app do not share the durable Web K session store, so Safari must fail
    # closed before generating or handing off a Telegram login token.
    assert "function isJerkgramStandalone(): boolean" in patched
    assert "matchMedia('(display-mode: standalone)')" in patched
    assert "navigatorWithStandalone.standalone === true" in patched
    assert "if(!isJerkgramStandalone())" in patched
    assert "Add Jerkgram Notifications to the Home Screen first." in patched

    # The foreground handoff credential is a local byte reference and is dropped
    # immediately after Base64URL conversion. Stock Web K may keep its own QR token
    # in memory for polling, but pairing must never persist or log its local token.
    assert "freshToken = undefined" in patched
    assert "localStorage" not in patched
    assert "sessionStorage" not in patched
    assert "indexedDB" not in patched
    assert "console.log(token" not in patched
    assert "console.error(token" not in patched

    # Do not claim the custom-scheme open failed based on a Safari/PWA visibility
    # timer. Native approval and Web K auth state are the real sources of truth.
    assert "Approve in Jerkgram, then return here" in patched
    assert "Jerkgram could not be opened." not in patched
    assert "openTimer" not in patched
    assert "window.setTimeout" not in patched

    # Preserve stock Web K's 2FA continuation. After native acceptLoginToken,
    # SESSION_PASSWORD_NEEDED must still route into PasswordCard.
    assert "case 'SESSION_PASSWORD_NEEDED':" in patched
    assert "navigate({name: 'password'});" in patched

    assert "Connection request expired. Try again." in patched
    assert "Could not connect to Telegram. Try again." in patched
    assert patched.count("Jerkgram Push Companion one-tap pairing") == 1
    assert patched.count("Jerkgram Push Companion primary pairing action") == 1

    # Idempotent: no duplicated helper, capture hook or button.
    result2 = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert result2.returncode == 0, result2.stderr + result2.stdout
    patched2 = target.read_text()
    assert patched2.count("Jerkgram Push Companion one-tap pairing") == 1
    assert patched2.count("Jerkgram Push Companion primary pairing action") == 1
    assert patched2.count("onJerkgramToken?.(loginToken.token)") == 1
