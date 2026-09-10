#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
SIGN_QR = ROOT / "src/pages/cards/SignQRCard.tsx"

if not SIGN_QR.exists():
    raise SystemExit(f"[jerkgram-pairing-webk] missing {SIGN_QR}")

source = SIGN_QR.read_text()
marker = "// MARK: Jerkgram Push Companion one-tap pairing"

state_anchor = """  let lastDrawnToken: Uint8Array | number[] | undefined;\n  let QRCodeStylingCtor: any;\n"""
helper = state_anchor + """\n  // MARK: Jerkgram Push Companion one-tap pairing\n  function connectWithJerkgram() {\n    if(!lastDrawnToken) return;\n\n    // Reuse the exact short-lived auth.exportLoginToken value already used for\n    // Telegram's QR login. Jerkgram accepts it with auth.acceptLoginToken; no\n    // phone number, SMS code, 2FA password or native MTProto auth key leaves the\n    // native client.\n    const encoded = bytesToBase64(lastDrawnToken);\n    const token = fixBase64String(encoded, true);\n    window.location.assign('jerkgram://push/authorize?token=' + encodeURIComponent(token));\n  }\n"""

if marker not in source:
    if state_anchor not in source:
        raise SystemExit("[jerkgram-pairing-webk] state anchor not found")
    source = source.replace(state_anchor, helper, 1)

button_marker = "{/* Jerkgram Push Companion primary pairing action */}"
render_anchor = """      {helpList}\n      <Button\n        class=\"btn-primary btn-secondary btn-primary-transparent primary\"\n"""
render_injection = """      {helpList}\n      {/* Jerkgram Push Companion primary pairing action */}\n      <Button\n        primaryFilled\n        large\n        onClick={connectWithJerkgram}\n      >\n        Connect with Jerkgram\n      </Button>\n      <Button\n        class=\"btn-primary btn-secondary btn-primary-transparent primary\"\n"""

if button_marker not in source:
    if render_anchor not in source:
        raise SystemExit("[jerkgram-pairing-webk] render anchor not found")
    source = source.replace(render_anchor, render_injection, 1)

SIGN_QR.write_text(source)

print("[jerkgram-pairing-webk] OK")
print("  patched:", SIGN_QR)
