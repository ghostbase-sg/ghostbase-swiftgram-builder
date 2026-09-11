#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
MOUNT_AUTH = ROOT / "src/pages/mountAuthFlow.tsx"
SIGN_QR = ROOT / "src/pages/cards/SignQRCard.tsx"
BOOTSTRAP_IM = ROOT / "src/pages/bootstrapIm.ts"
APP_IM = ROOT / "src/lib/appImManager.ts"
SHELL = ROOT / "src/lib/jerkgramCompanionShell.ts"
PUSH = ROOT / "src/lib/jerkgramCompanionPush.ts"

for path in (MOUNT_AUTH, SIGN_QR, BOOTSTRAP_IM, APP_IM):
    if not path.exists():
        raise SystemExit(f"[jerkgram-minimal-ui] missing {path}")

# Fresh companion installations enter Web K's existing QR/login-token flow directly,
# never the phone-number card. Preserve the stock password state because Telegram
# can require 2FA after the native client approves a login token.
auth = MOUNT_AUTH.read_text()
old_auth = "case 'authStateSignIn':\n      return {name: 'signIn'};"
new_auth = "case 'authStateSignIn':\n      return {name: 'signQR'};"
password_auth = "case 'authStatePassword':\n      return {name: 'password'};"
if password_auth not in auth:
    raise SystemExit("[jerkgram-minimal-ui] stock authStatePassword route missing")
if new_auth not in auth:
    if auth.count(old_auth) != 1:
        raise SystemExit(f"[jerkgram-minimal-ui] expected one authStateSignIn anchor, found {auth.count(old_auth)}")
    auth = auth.replace(old_auth, new_auth, 1)
if password_auth not in auth:
    raise SystemExit("[jerkgram-minimal-ui] authStatePassword route lost after patch")
MOUNT_AUTH.write_text(auth)

# The pairing patch must already have run. This layer is presentation-only: keep
# Web K's existing export/migrate/import/success/password loop intact and replace
# only the visible QR-oriented return block. The QR host remains hidden because
# Web K still owns token rotation and paintQR uses that host as part of its normal
# lifecycle.
qr = SIGN_QR.read_text()
for prerequisite in (
    "auth.exportLoginToken",
    "auth.importLoginToken",
    "auth.loginTokenSuccess",
    "SESSION_PASSWORD_NEEDED",
    "navigate({name: 'password'})",
    "jerkgram://push/authorize",
    "toIm()",
    "function isJerkgramStandalone(): boolean",
    "Jerkgram Push Companion primary pairing action",
):
    if prerequisite not in qr:
        raise SystemExit(f"[jerkgram-minimal-ui] SignQRCard prerequisite missing: {prerequisite}")

minimal_marker = "{/* MARK: Jerkgram Notifications minimal auth surface */}"
if minimal_marker not in qr:
    render_scope = qr.find("  /* ---------- render ---------- */")
    search_from = render_scope if render_scope >= 0 else 0
    return_start = qr.find("  return (", search_from)
    if return_start < 0:
        raise SystemExit("[jerkgram-minimal-ui] SignQRCard return block start not found")
    return_end_marker = "\n  );\n}"
    return_end_pos = qr.find(return_end_marker, return_start)
    if return_end_pos < 0:
        raise SystemExit("[jerkgram-minimal-ui] SignQRCard return block end not found")
    if qr.find("  return (", return_start + 1, return_end_pos) >= 0:
        raise SystemExit("[jerkgram-minimal-ui] ambiguous SignQRCard return scope")

    minimal_return = r'''  return (
    <AuthCard inputWrapper={false}>
      {/* MARK: Jerkgram Notifications minimal auth surface */}
      <div ref={stickerHost} style={{display: 'none'}} />
      <div style={{'text-align': 'center', padding: '12px 8px 20px'}}>
        <h1 style={{margin: '0 0 10px', 'font-size': '28px'}}>Jerkgram Notifications</h1>
        <p class="secondary" style={{margin: 0}}>
          Connect Jerkgram to enable Telegram notifications.
        </p>
      </div>
      {/* Jerkgram Push Companion primary pairing action */}
      <Button
        primaryFilled
        large
        disabled={!isJerkgramStandalone() || pairingBusy()}
        onClick={connectWithJerkgram}
      >
        {pairingBusy() ? 'Opening Jerkgram…' : 'Connect with Jerkgram'}
      </Button>
      {!isJerkgramStandalone() && (
        <p class="secondary" style={{'text-align': 'center', 'font-size': '13px', margin: '12px 8px 0'}}>
          Add Jerkgram Notifications to the Home Screen first. Open it from the Home Screen to connect.
        </p>
      )}
      {pairingStatus() && (
        <p class="secondary" style={{'text-align': 'center', 'font-size': '13px', margin: '12px 8px 0'}}>
          {pairingStatus()}
        </p>
      )}
      <p class="secondary" style={{'text-align': 'center', 'font-size': '13px', margin: '16px 8px 0'}}>
        Jerkgram must already be installed and logged in.
      </p>
    </AuthCard>
  );'''
    return_end = return_end_pos + len("\n  );")
    qr = qr[:return_start] + minimal_return + qr[return_end:]

# Fail-fast invariants: auth protocol markers from Web K must survive this patch.
for invariant in (
    "auth.exportLoginToken",
    "auth.importLoginToken",
    "auth.loginTokenSuccess",
    "SESSION_PASSWORD_NEEDED",
    "navigate({name: 'password'})",
    "jerkgram://push/authorize",
    "disabled={!isJerkgramStandalone() || pairingBusy()}",
    "Add Jerkgram Notifications to the Home Screen first.",
    "Open it from the Home Screen to connect.",
    minimal_marker,
):
    if invariant not in qr:
        raise SystemExit(f"[jerkgram-minimal-ui] SignQRCard invariant missing after UI patch: {invariant}")
if "navigate({name: 'signIn'})" in qr:
    raise SystemExit("[jerkgram-minimal-ui] phone-login cancel path survived minimal auth surface")
SIGN_QR.write_text(qr)

# A small runtime owns only Web Push subscription/registration. Opening the
# companion does not bootstrap chats, media, calls, sidebars or normal Web K IM.
PUSH.write_text(r'''import {SETTINGS_INIT} from '@config/state';
import apiManagerProxy from '@lib/apiManagerProxy';
import webPushApiManager from '@lib/webPushApiManager';

let started = false;

export function startJerkgramCompanionPushRuntime(): void {
  if(started) return;
  started = true;

  webPushApiManager.setSettings({
    ...SETTINGS_INIT.notifications,
    baseUrl: new URL('./', location.href).toString()
  });
  webPushApiManager.start();
}

export async function ensureJerkgramPushRegistered(): Promise<boolean> {
  if(!webPushApiManager.isAvailable || Notification.permission !== 'granted') {
    return false;
  }

  let tokenData = await webPushApiManager.getSubscription();
  tokenData ||= await webPushApiManager.subscribe();
  if(!tokenData) return false;

  await apiManagerProxy.pushSingleManager.registerDevice(tokenData);
  return true;
}

export async function disconnectJerkgramCompanionPush(): Promise<void> {
  const tokenData = await webPushApiManager.getSubscription();
  if(tokenData) {
    // Re-enter Web K's own push manager before unregistering. This keeps the
    // account.unregisterDevice implementation and multi-account bookkeeping in
    // one stock owner even after a fresh PWA process was launched for Disconnect.
    await apiManagerProxy.pushSingleManager.registerDevice(tokenData);
    await apiManagerProxy.pushSingleManager.unregisterDevice(tokenData);
  }
  await webPushApiManager.unsubscribe();
}
''')

SHELL.write_text(r'''import apiManagerProxy from '@lib/apiManagerProxy';
import rootScope from '@lib/rootScope';
import {
  disconnectJerkgramCompanionPush,
  ensureJerkgramPushRegistered
} from '@lib/jerkgramCompanionPush';

let mounted = false;

function isStandalone(): boolean {
  const navigatorWithStandalone = navigator as Navigator & {standalone?: boolean};
  return window.matchMedia('(display-mode: standalone)').matches || navigatorWithStandalone.standalone === true;
}

function make<K extends keyof HTMLElementTagNameMap>(tag: K, text?: string): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);
  if(text !== undefined) element.textContent = text;
  return element;
}

function currentAccountLabel(): string {
  const user = apiManagerProxy.getUser(rootScope.myId.toUserId());
  const username = user?.username?.trim();
  if(username) return `@${username}`;

  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim();
  return displayName || 'Telegram account';
}

export default function mountJerkgramCompanionShell(): void {
  if(mounted) return;
  mounted = true;

  const style = make('style');
  style.textContent = `
    #jerkgram-notifications-shell{position:fixed;inset:0;z-index:2147483646;background:#f5f5f7;color:#111;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",sans-serif;display:flex;align-items:center;justify-content:center;padding:24px;box-sizing:border-box}
    #jerkgram-notifications-card{width:min(100%,420px);background:#fff;border-radius:24px;padding:28px;box-sizing:border-box;box-shadow:0 18px 60px rgba(0,0,0,.12)}
    #jerkgram-notifications-card h1{font-size:28px;line-height:1.12;margin:0 0 10px}
    #jerkgram-notifications-card p{font-size:15px;line-height:1.45;margin:0;color:#666}
    #jerkgram-notifications-account{margin-top:18px!important;color:#222!important;font-weight:600}
    #jerkgram-notifications-status{margin-top:12px!important;padding:13px 14px;border-radius:14px;background:#f2f2f7;color:#222!important}
    #jerkgram-notifications-enable,#jerkgram-notifications-disconnect{width:100%;margin-top:18px;border:0;border-radius:14px;padding:14px 16px;font:inherit;font-weight:600}
    #jerkgram-notifications-enable{background:#111;color:#fff}
    #jerkgram-notifications-disconnect{background:#f2f2f7;color:#b42318}
    #jerkgram-notifications-enable:disabled,#jerkgram-notifications-disconnect:disabled{opacity:.45}
  `;

  const shell = make('main');
  shell.id = 'jerkgram-notifications-shell';
  const card = make('section');
  card.id = 'jerkgram-notifications-card';
  const title = make('h1', 'Jerkgram Notifications');
  const intro = make('p', 'Notification companion for Jerkgram. After setup, this app can stay closed.');
  const account = make('p', `Connected as ${currentAccountLabel()}`);
  account.id = 'jerkgram-notifications-account';
  const status = make('p');
  status.id = 'jerkgram-notifications-status';
  const enable = make('button');
  enable.id = 'jerkgram-notifications-enable';
  enable.type = 'button';
  enable.textContent = 'Enable Notifications';
  const disconnect = make('button');
  disconnect.id = 'jerkgram-notifications-disconnect';
  disconnect.type = 'button';
  disconnect.textContent = 'Disconnect';

  card.append(title, intro, account, status, enable, disconnect);
  shell.append(card);
  document.head.append(style);
  document.body.append(shell);

  const renderState = async() => {
    disconnect.disabled = false;

    if(!('Notification' in window) || !('serviceWorker' in navigator)) {
      status.textContent = 'Web Push is not available in this browser.';
      enable.disabled = true;
      return;
    }

    if(!isStandalone()) {
      status.textContent = 'Add Jerkgram Notifications to the Home Screen, then open it from there.';
      enable.disabled = true;
      return;
    }

    if(Notification.permission === 'denied') {
      status.textContent = 'Notifications are blocked. Allow them in iOS Settings to continue.';
      enable.disabled = true;
      return;
    }

    if(Notification.permission === 'granted') {
      enable.disabled = true;
      enable.textContent = 'Checking…';
      try {
        const registered = await ensureJerkgramPushRegistered();
        if(registered) {
          status.textContent = 'Notifications are active. Jerkgram Notifications can now stay closed.';
          enable.textContent = 'Notifications Enabled';
        } else {
          status.textContent = 'Could not register Web Push on this device.';
          enable.textContent = 'Retry';
          enable.disabled = false;
        }
      } catch {
        console.error('Jerkgram push registration failed');
        status.textContent = 'Push registration failed. Try again.';
        enable.textContent = 'Retry';
        enable.disabled = false;
      }
      return;
    }

    status.textContent = 'Connected. One last step: allow notifications on this device.';
    enable.textContent = 'Enable Notifications';
    enable.disabled = false;
  };

  enable.addEventListener('click', async() => {
    enable.disabled = true;
    if(Notification.permission === 'default') {
      await Notification.requestPermission();
    }
    await renderState();
  });

  disconnect.addEventListener('click', async() => {
    enable.disabled = true;
    disconnect.disabled = true;
    status.textContent = 'Disconnecting…';
    try {
      await disconnectJerkgramCompanionPush();
      await rootScope.managers.apiManager.logOut();
      window.location.reload();
    } catch {
      console.error('Jerkgram companion disconnect failed');
      status.textContent = 'Could not disconnect. Try again.';
      disconnect.disabled = false;
      await renderState();
    }
  });

  void renderState();
}
''')

# The post-auth entry point is deliberately notification-only. No dynamic import
# of appDialogsManager means its large chat/IM dependency graph is not requested.
BOOTSTRAP_IM.write_text(r'''import rootScope from '@lib/rootScope';
import mountJerkgramCompanionShell from '@lib/jerkgramCompanionShell';
import {startJerkgramCompanionPushRuntime} from '@lib/jerkgramCompanionPush';

import {disposeActiveAuthFlow} from '@/pages/mountAuthFlow';

let bootstrapped = false;

export async function bootstrapIm(): Promise<void> {
  if(bootstrapped) return;
  bootstrapped = true;

  await rootScope.managers.appStateManager.pushToState('authState', {_: 'authStateSignedIn'});
  startJerkgramCompanionPushRuntime();
  mountJerkgramCompanionShell();
  disposeActiveAuthFlow();
  document.body.classList.remove('has-auth-pages');
}

export default bootstrapIm;
''')

# Remove the previous overlay injection if an earlier PoC patch was materialized.
im = APP_IM.read_text()
im = im.replace("import mountJerkgramCompanionShell from '@lib/jerkgramCompanionShell';\n", "")
im = im.replace("\n    mountJerkgramCompanionShell();\n", "\n")
APP_IM.write_text(im)

print("[jerkgram-minimal-ui] OK")
print("  patched:", MOUNT_AUTH)
print("  presentation-only:", SIGN_QR)
print("  replaced:", BOOTSTRAP_IM)
print("  created:", PUSH)
print("  created:", SHELL)
