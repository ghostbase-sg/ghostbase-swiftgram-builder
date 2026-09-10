#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
SIGN_QR = ROOT / "src/pages/cards/SignQRCard.tsx"

if not SIGN_QR.exists():
    raise SystemExit(f"[jerkgram-pairing-webk] missing {SIGN_QR}")

source = SIGN_QR.read_text()
marker = "// MARK: Jerkgram Push Companion one-tap pairing"

# Pairing status is UI-only and intentionally ephemeral. Do not persist the
# Telegram login token or any pairing state in browser storage.
solid_old = "import {onCleanup, onMount} from 'solid-js';"
solid_new = "import {createSignal, onCleanup, onMount} from 'solid-js';"
if solid_new not in source:
    if solid_old not in source:
        raise SystemExit("[jerkgram-pairing-webk] Solid import anchor not found")
    source = source.replace(solid_old, solid_new, 1)

# Preserve Telegram Web K as the sole owner of exportLoginToken, DC migration,
# importLoginToken and loginTokenSuccess. The optional callback only exposes the
# exact regular loginToken produced by this particular iterate() call to the
# foreground pairing button, so the background QR poller cannot overwrite the
# handoff token through lastDrawnToken between the API response and URL creation.
iterate_old = "async function iterate(QRCodeStyling: any, isLoop: boolean): Promise<boolean> {"
iterate_new = "async function iterate(QRCodeStyling: any, isLoop: boolean, onJerkgramToken?: (token: Uint8Array | number[]) => void): Promise<boolean> {"
if iterate_new not in source:
    if source.count(iterate_old) != 1:
        raise SystemExit(f"[jerkgram-pairing-webk] expected one iterate signature, found {source.count(iterate_old)}")
    source = source.replace(iterate_old, iterate_new, 1)

capture_anchor = "    if(!prevToken || !bytesCmp(prevToken, loginToken.token)) {"
capture_line = "    onJerkgramToken?.(loginToken.token);\n\n"
if capture_line not in source:
    if source.count(capture_anchor) != 1:
        raise SystemExit(f"[jerkgram-pairing-webk] expected one regular-token anchor, found {source.count(capture_anchor)}")
    source = source.replace(capture_anchor, capture_line + capture_anchor, 1)

state_anchor = """  let lastDrawnToken: Uint8Array | number[] | undefined;\n  let QRCodeStylingCtor: any;\n"""
helper = state_anchor + """\n  // MARK: Jerkgram Push Companion one-tap pairing\n  const [pairingBusy, setPairingBusy] = createSignal(false);\n  const [pairingStatus, setPairingStatus] = createSignal('');\n\n  async function connectWithJerkgram() {\n    if(pairingBusy()) return;\n    if(!lastDrawnToken || !QRCodeStylingCtor) {\n      setPairingStatus('Could not connect to Telegram. Try again.');\n      return;\n    }\n\n    setPairingBusy(true);\n    setPairingStatus('');\n\n    // Ask the existing Web K QR-login iterator for a token now, immediately\n    // before native handoff. The callback is tied to this exact invocation, so\n    // concurrent background QR polling cannot substitute another token.\n    let freshToken: Uint8Array | number[] | undefined;\n    const needBreak = await iterate(QRCodeStylingCtor, false, (token) => {\n      freshToken = token;\n    });\n\n    if(needBreak) {\n      freshToken = undefined;\n      setPairingBusy(false);\n      setPairingStatus('Could not connect to Telegram. Try again.');\n      return;\n    }\n    if(!freshToken) {\n      setPairingBusy(false);\n      setPairingStatus('Connection request expired. Try again.');\n      return;\n    }\n\n    // Copy only long enough to form the URL-safe handoff, then drop the local\n    // byte reference. No auth key/session database/cookie is transferred.\n    const encoded = bytesToBase64(freshToken);\n    const token = fixBase64String(encoded, true);\n    freshToken = undefined;\n    const deepLink = 'jerkgram://push/authorize?token=' + encodeURIComponent(token);\n\n    // iOS does not provide a synchronous success result for a custom-scheme open.\n    // Treat a page visibility transition as evidence that Jerkgram opened. If the\n    // PWA remains visible, surface a friendly retry state instead of an RPC error.\n    let didLeavePage = false;\n    let openTimer: number | undefined;\n    const cleanupOpenProbe = () => {\n      if(openTimer !== undefined) {\n        window.clearTimeout(openTimer);\n        openTimer = undefined;\n      }\n      document.removeEventListener('visibilitychange', onPairingVisibilityChange);\n    };\n    const onPairingVisibilityChange = () => {\n      if(document.hidden) {\n        didLeavePage = true;\n        if(openTimer !== undefined) {\n          window.clearTimeout(openTimer);\n          openTimer = undefined;\n        }\n      } else if(didLeavePage) {\n        cleanupOpenProbe();\n        setPairingBusy(false);\n        setPairingStatus('');\n      }\n    };\n    document.addEventListener('visibilitychange', onPairingVisibilityChange);\n    openTimer = window.setTimeout(() => {\n      if(!didLeavePage && !document.hidden) {\n        cleanupOpenProbe();\n        setPairingBusy(false);\n        setPairingStatus('Jerkgram could not be opened.');\n      }\n    }, 1500);\n\n    window.location.assign(deepLink);\n  }\n"""

if marker not in source:
    if source.count(state_anchor) != 1:
        raise SystemExit(f"[jerkgram-pairing-webk] expected one state anchor, found {source.count(state_anchor)}")
    source = source.replace(state_anchor, helper, 1)

button_marker = "{/* Jerkgram Push Companion primary pairing action */}"
render_anchor = """      {helpList}\n      <Button\n        class=\"btn-primary btn-secondary btn-primary-transparent primary\"\n"""
render_injection = """      {helpList}\n      {/* Jerkgram Push Companion primary pairing action */}\n      <Button\n        primaryFilled\n        large\n        disabled={pairingBusy()}\n        onClick={connectWithJerkgram}\n      >\n        {pairingBusy() ? 'Opening Jerkgram…' : 'Connect with Jerkgram'}\n      </Button>\n      {pairingStatus() && (\n        <p class=\"secondary\" style={{'text-align': 'center', 'font-size': '13px', margin: '12px 8px 0'}}>\n          {pairingStatus()}\n        </p>\n      )}\n      <Button\n        class=\"btn-primary btn-secondary btn-primary-transparent primary\"\n"""

if button_marker not in source:
    if source.count(render_anchor) != 1:
        raise SystemExit(f"[jerkgram-pairing-webk] expected one render anchor, found {source.count(render_anchor)}")
    source = source.replace(render_anchor, render_injection, 1)

# Fail closed if an upstream change left a partial application behind.
for invariant in (
    solid_new,
    iterate_new,
    "onJerkgramToken?.(loginToken.token)",
    marker,
    button_marker,
    "await iterate(QRCodeStylingCtor, false, (token) =>",
    "bytesToBase64(freshToken)",
    "Jerkgram could not be opened.",
    "Connection request expired. Try again.",
    "Could not connect to Telegram. Try again.",
):
    if invariant not in source:
        raise SystemExit(f"[jerkgram-pairing-webk] invariant missing after patch: {invariant}")

SIGN_QR.write_text(source)

print("[jerkgram-pairing-webk] OK")
print("  patched:", SIGN_QR)
