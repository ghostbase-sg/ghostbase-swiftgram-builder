#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
MOUNT_AUTH = ROOT / "src/pages/mountAuthFlow.tsx"
SIGN_QR = ROOT / "src/pages/cards/SignQRCard.tsx"
APP_IM = ROOT / "src/lib/appImManager.ts"
SHELL = ROOT / "src/lib/jerkgramCompanionShell.ts"

for path in (MOUNT_AUTH, SIGN_QR, APP_IM):
    if not path.exists():
        raise SystemExit(f"[jerkgram-minimal-ui] missing {path}")

# A fresh companion should never start at Web K's phone-number UI.
auth = MOUNT_AUTH.read_text()
old_auth = "case 'authStateSignIn':\n      return {name: 'signIn'};"
new_auth = "case 'authStateSignIn':\n      return {name: 'signQR'};"
if new_auth not in auth:
    if old_auth not in auth:
        raise SystemExit("[jerkgram-minimal-ui] authStateSignIn anchor not found")
    auth = auth.replace(old_auth, new_auth, 1)
MOUNT_AUTH.write_text(auth)

# The one-tap pairing patch must run first. Replace the QR/phone-oriented card
# with a single-purpose Jerkgram pairing card, while retaining Telegram's
# official login-token protocol and the normal post-auth bootstrap.
qr_before = SIGN_QR.read_text()
for marker in ("auth.exportLoginToken", "jerkgram://push/authorize", "toIm()"):
    if marker not in qr_before:
        raise SystemExit(f"[jerkgram-minimal-ui] SignQRCard prerequisite missing: {marker}")

SIGN_QR.write_text(r'''import {createSignal, onCleanup, onMount} from 'solid-js';

import Button from '@components/buttonTsx';
import bytesToBase64 from '@helpers/bytes/bytesToBase64';
import fixBase64String from '@helpers/fixBase64String';
import pause from '@helpers/schedulers/pause';
import type {DcId} from '@types';
import {AuthAuthorization, AuthLoginToken} from '@layer';
import App from '@config/app';
import AccountController from '@lib/accounts/accountController';
import rootScope from '@lib/rootScope';

import AuthCard from '@/pages/AuthCard';
import {CardSpec, useAuthFlow} from '@/pages/authFlow';

if(import.meta.hot) import.meta.hot.accept();

type Spec = Extract<CardSpec, {name: 'signQR'}>;
const FETCH_INTERVAL = 3;

export default function SignQRCard(_props: {spec: Spec}) {
  const {managers, navigate, toIm} = useAuthFlow();
  const [ready, setReady] = createSignal(false);
  let stopped = false;
  let lastLoginToken: Uint8Array | number[] | undefined;

  function connectWithJerkgram() {
    if(!lastLoginToken) return;
    const encoded = bytesToBase64(lastLoginToken);
    const token = fixBase64String(encoded, true);
    // The short-lived Telegram login token is handed directly to the installed
    // native Jerkgram. It is never placed in this page URL or sent to Jerkgram infrastructure.
    window.location.assign('jerkgram://push/authorize?token=' + encodeURIComponent(token));
  }

  const onUserAuth = () => {
    stopped = true;
  };
  rootScope.addEventListener('user_auth', onUserAuth, {once: true});

  const options: {dcId?: DcId, ignoreErrors: true} = {ignoreErrors: true};

  async function iterate(): Promise<boolean> {
    try {
      const userIds = await AccountController.getUserIds();
      let loginToken = await managers.apiManager.invokeApi('auth.exportLoginToken', {
        api_id: App.id,
        api_hash: App.hash,
        except_ids: userIds.map((userId) => userId.toUserId())
      }, {ignoreErrors: true});

      if(loginToken._ === 'auth.loginTokenMigrateTo') {
        if(!options.dcId) {
          options.dcId = loginToken.dc_id as DcId;
          managers.apiManager.setBaseDcId(loginToken.dc_id);
        }
        loginToken = await managers.apiManager.invokeApi('auth.importLoginToken', {
          token: loginToken.token
        }, options) as AuthLoginToken.authLoginToken;
      }

      if(loginToken._ === 'auth.loginTokenSuccess') {
        const authorization = loginToken.authorization as any as AuthAuthorization.authAuthorization;
        await managers.apiManager.setUser(authorization.user);
        await toIm();
        return true;
      }

      lastLoginToken = loginToken.token;
      setReady(true);

      const timestamp = Date.now() / 1000;
      const diff = loginToken.expires - timestamp - await managers.timeManager.getServerTimeOffset();
      await pause(diff > FETCH_INTERVAL ? 1e3 * FETCH_INTERVAL : 1e3 * diff | 0);
      return false;
    } catch(err) {
      if((err as ApiError).type === 'SESSION_PASSWORD_NEEDED') {
        // Keep Telegram's own fallback if the account requires password confirmation.
        navigate({name: 'password'});
      } else if((err as ApiError).type !== 'AUTH_TOKEN_EXPIRED') {
        console.error('Jerkgram companion pairing error:', err);
        stopped = true;
      }
      return false;
    }
  }

  onMount(async() => {
    managers.appStateManager.pushToState('authState', {_: 'authStateSignQr'});
    while(!stopped) {
      if(await iterate()) break;
    }
  });

  onCleanup(() => {
    stopped = true;
    rootScope.removeEventListener('user_auth', onUserAuth);
  });

  return (
    <AuthCard inputWrapper={false}>
      <div style={{'text-align': 'center', padding: '12px 8px 20px'}}>
        <h1 style={{margin: '0 0 10px', 'font-size': '28px'}}>Jerkgram Notifications</h1>
        <p class="secondary" style={{margin: 0}}>
          Connect this notification companion to the Telegram account already signed in to Jerkgram.
        </p>
      </div>
      <Button primaryFilled large disabled={!ready()} onClick={connectWithJerkgram}>
        Connect with Jerkgram
      </Button>
      <p class="secondary" style={{'text-align': 'center', 'font-size': '13px', margin: '16px 8px 0'}}>
        No phone number or SMS code is requested here.
      </p>
    </AuthCard>
  );
}
''')

SHELL.write_text(r'''import uiNotificationsManager from '@lib/uiNotificationsManager';

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

export default function mountJerkgramCompanionShell(): void {
  if(mounted) return;
  mounted = true;

  const style = make('style');
  style.textContent = `
    #jerkgram-notifications-shell{position:fixed;inset:0;z-index:2147483646;background:#f5f5f7;color:#111;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",sans-serif;display:flex;align-items:center;justify-content:center;padding:24px;box-sizing:border-box}
    #jerkgram-notifications-card{width:min(100%,420px);background:#fff;border-radius:24px;padding:28px;box-sizing:border-box;box-shadow:0 18px 60px rgba(0,0,0,.12)}
    #jerkgram-notifications-card h1{font-size:28px;line-height:1.12;margin:0 0 10px}
    #jerkgram-notifications-card p{font-size:15px;line-height:1.45;margin:0;color:#666}
    #jerkgram-notifications-status{margin-top:20px!important;padding:13px 14px;border-radius:14px;background:#f2f2f7;color:#222!important}
    #jerkgram-notifications-enable{width:100%;margin-top:18px;border:0;border-radius:14px;padding:14px 16px;font:inherit;font-weight:600;background:#111;color:#fff}
    #jerkgram-notifications-enable:disabled{opacity:.45}
  `;

  const shell = make('main');
  shell.id = 'jerkgram-notifications-shell';
  const card = make('section');
  card.id = 'jerkgram-notifications-card';
  const title = make('h1', 'Jerkgram Notifications');
  const intro = make('p', 'This companion only keeps Telegram Web Push available for Jerkgram. You can close it after setup.');
  const status = make('p');
  status.id = 'jerkgram-notifications-status';
  const enable = make('button');
  enable.id = 'jerkgram-notifications-enable';
  enable.type = 'button';
  enable.textContent = 'Enable Notifications';

  card.append(title, intro, status, enable);
  shell.append(card);
  document.head.append(style);
  document.body.append(shell);

  const renderState = async() => {
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
      status.textContent = 'Notifications are active. Jerkgram Notifications can now stay closed.';
      enable.textContent = 'Notifications Enabled';
      enable.disabled = true;
      await uiNotificationsManager.onPushConditionsChange();
      return;
    }

    status.textContent = 'Connected. One last step: allow notifications on this device.';
    enable.disabled = false;
  };

  enable.addEventListener('click', async() => {
    enable.disabled = true;
    const permission = await Notification.requestPermission();
    if(permission === 'granted') {
      await uiNotificationsManager.onPushConditionsChange();
    }
    await renderState();
  });

  void renderState();
}
''')

im = APP_IM.read_text()
import_anchor = "import uiNotificationsManager from '@lib/uiNotificationsManager';"
import_line = "import mountJerkgramCompanionShell from '@lib/jerkgramCompanionShell';"
if import_line not in im:
    if import_anchor not in im:
        raise SystemExit("[jerkgram-minimal-ui] appImManager import anchor not found")
    im = im.replace(import_anchor, import_anchor + "\n" + import_line, 1)
call_anchor = "    uiNotificationsManager.constructAndStartAll();"
call_line = "    mountJerkgramCompanionShell();"
if call_line not in im:
    if call_anchor not in im:
        raise SystemExit("[jerkgram-minimal-ui] notifications construct anchor not found")
    im = im.replace(call_anchor, call_anchor + "\n\n" + call_line, 1)
APP_IM.write_text(im)

print("[jerkgram-minimal-ui] OK")
print("  patched:", MOUNT_AUTH)
print("  replaced:", SIGN_QR)
print("  created:", SHELL)
print("  patched:", APP_IM)
