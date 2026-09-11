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
helper = state_anchor + """\n  // MARK: Jerkgram Push Companion one-tap pairing\n  const [pairingBusy, setPairingBusy] = createSignal(false);\n  const [pairingStatus, setPairingStatus] = createSignal('');\n  let resumeProbeInFlight = false;\n\n  function isJerkgramStandalone(): boolean {\n    const navigatorWithStandalone = navigator as Navigator & {standalone?: boolean};\n    return window.matchMedia('(display-mode: standalone)').matches || navigatorWithStandalone.standalone === true;\n  }\n\n  async function resumeJerkgramPairing() {\n    if(stopped || document.hidden || resumeProbeInFlight) return;\n\n    resumeProbeInFlight = true;\n    try {\n      // iOS can suspend the normal QR polling timer while Jerkgram is in the\n      // foreground. Probe once immediately on return so Web K can observe the\n      // accepted login token and route to loginTokenSuccess or PasswordCard.\n      await iterate(undefined, false);\n    } finally {\n      resumeProbeInFlight = false;\n    }\n  }\n\n  const onJerkgramVisibilityChange = () => {\n    if(!document.hidden) void resumeJerkgramPairing();\n  };\n  const onJerkgramPageShow = () => {\n    void resumeJerkgramPairing();\n  };\n  const onJerkgramFocus = () => {\n    void resumeJerkgramPairing();\n  };\n\n  async function connectWithJerkgram() {\n    if(pairingBusy()) return;\n\n    // The durable Web K authorization must be created in the installed Home\n    // Screen web app. Safari and the standalone web app have separate local\n    // storage, so pairing in Safari would authorize the wrong browser context.\n    if(!isJerkgramStandalone()) {\n      setPairingStatus('Add Jerkgram Notifications to the Home Screen first.');\n      return;\n    }\n\n    setPairingBusy(true);\n    setPairingStatus('');\n\n    // Ask the existing Web K QR-login iterator for a token now, immediately\n    // before native handoff. This foreground request deliberately does not depend\n    // on the hidden QR renderer having loaded or painted anything first. Passing\n    // no QR constructor keeps token acquisition independent from presentation.\n    let freshToken: Uint8Array | number[] | undefined;\n    const needBreak = await iterate(undefined, false, (token) => {\n      freshToken = token;\n    });\n\n    if(needBreak) {\n      freshToken = undefined;\n      setPairingBusy(false);\n      setPairingStatus('Could not connect to Telegram. Try again.');\n      return;\n    }\n    if(!freshToken) {\n      setPairingBusy(false);\n      setPairingStatus('Connection request expired. Try again.');\n      return;\n    }\n\n    // Copy only long enough to form the URL-safe handoff, then drop the local\n    // byte reference. No auth key/session database/cookie is transferred.\n    const encoded = bytesToBase64(freshToken);\n    const token = fixBase64String(encoded, true);\n    freshToken = undefined;\n    const deepLink = 'jerkgram://push/authorize?token=' + encodeURIComponent(token);\n\n    // Custom-scheme navigation has no trustworthy synchronous success signal on\n    // iOS. Do not guess from visibility timing. Native approval plus Web K's own\n    // auth state (loginTokenSuccess / SESSION_PASSWORD_NEEDED) are authoritative.\n    setPairingBusy(false);\n    setPairingStatus('Approve in Jerkgram, then return here…');\n    window.location.assign(deepLink);\n  }\n"""

if marker not in source:
    if source.count(state_anchor) != 1:
        raise SystemExit(f"[jerkgram-pairing-webk] expected one state anchor, found {source.count(state_anchor)}")
    source = source.replace(state_anchor, helper, 1)

on_mount_anchor = """  onMount(async() => {\n    managers.appStateManager.pushToState('authState', {_: 'authStateSignQr'});\n"""
on_mount_patched = """  onMount(async() => {\n    document.addEventListener('visibilitychange', onJerkgramVisibilityChange);\n    window.addEventListener('pageshow', onJerkgramPageShow);\n    window.addEventListener('focus', onJerkgramFocus);\n\n    managers.appStateManager.pushToState('authState', {_: 'authStateSignQr'});\n"""
if on_mount_patched not in source:
    if source.count(on_mount_anchor) != 1:
        raise SystemExit(f"[jerkgram-pairing-webk] expected one onMount anchor, found {source.count(on_mount_anchor)}")
    source = source.replace(on_mount_anchor, on_mount_patched, 1)

on_cleanup_anchor = """  onCleanup(() => {\n    stopped = true;\n"""
on_cleanup_patched = """  onCleanup(() => {\n    document.removeEventListener('visibilitychange', onJerkgramVisibilityChange);\n    window.removeEventListener('pageshow', onJerkgramPageShow);\n    window.removeEventListener('focus', onJerkgramFocus);\n    stopped = true;\n"""
if on_cleanup_patched not in source:
    if source.count(on_cleanup_anchor) != 1:
        raise SystemExit(f"[jerkgram-pairing-webk] expected one onCleanup anchor, found {source.count(on_cleanup_anchor)}")
    source = source.replace(on_cleanup_anchor, on_cleanup_patched, 1)

button_marker = "{/* Jerkgram Push Companion primary pairing action */}"
render_anchor = """      {helpList}\n      <Button\n        class=\"btn-primary btn-secondary btn-primary-transparent primary\"\n"""
render_injection = """      {helpList}\n      {/* Jerkgram Push Companion primary pairing action */}\n      <Button\n        primaryFilled\n        large\n        disabled={!isJerkgramStandalone() || pairingBusy()}\n        onClick={connectWithJerkgram}\n      >\n        {pairingBusy() ? 'Opening Jerkgram…' : 'Connect with Jerkgram'}\n      </Button>\n      {!isJerkgramStandalone() && (\n        <p class=\"secondary\" style={{'text-align': 'center', 'font-size': '13px', margin: '12px 8px 0'}}>\n          Add Jerkgram Notifications to the Home Screen first. Open it from the Home Screen to connect.\n        </p>\n      )}\n      {pairingStatus() && (\n        <p class=\"secondary\" style={{'text-align': 'center', 'font-size': '13px', margin: '12px 8px 0'}}>\n          {pairingStatus()}\n        </p>\n      )}\n      <Button\n        class=\"btn-primary btn-secondary btn-primary-transparent primary\"\n"""

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
    "function isJerkgramStandalone(): boolean",
    "matchMedia('(display-mode: standalone)')",
    "if(!isJerkgramStandalone())",
    "Add Jerkgram Notifications to the Home Screen first.",
    "async function resumeJerkgramPairing()",
    "await iterate(undefined, false);",
    "document.addEventListener('visibilitychange', onJerkgramVisibilityChange)",
    "window.addEventListener('pageshow', onJerkgramPageShow)",
    "window.addEventListener('focus', onJerkgramFocus)",
    "document.removeEventListener('visibilitychange', onJerkgramVisibilityChange)",
    "window.removeEventListener('pageshow', onJerkgramPageShow)",
    "window.removeEventListener('focus', onJerkgramFocus)",
    "await iterate(undefined, false, (token) =>",
    "bytesToBase64(freshToken)",
    "Approve in Jerkgram, then return here",
    "Connection request expired. Try again.",
    "Could not connect to Telegram. Try again.",
):
    if invariant not in source:
        raise SystemExit(f"[jerkgram-pairing-webk] invariant missing after patch: {invariant}")

if "Jerkgram could not be opened." in source:
    raise SystemExit("[jerkgram-pairing-webk] stale visibility-based open failure survived")

SIGN_QR.write_text(source)

print("[jerkgram-pairing-webk] OK")
print("  patched:", SIGN_QR)
