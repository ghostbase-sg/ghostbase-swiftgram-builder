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

# Fresh companion installations enter the official login-token flow directly,
# never Web K's phone-number screen.
auth = MOUNT_AUTH.read_text()
old_auth = "case 'authStateSignIn':\n      return {name: 'signIn'};"
new_auth = "case 'authStateSignIn':\n      return {name: 'signQR'};"
if new_auth not in auth:
    if old_auth not in auth:
        raise SystemExit("[jerkgram-minimal-ui] authStateSignIn anchor not found")
    auth = auth.replace(old_auth, new_auth, 1)
MOUNT_AUTH.write_text(auth)

# The earlier one-tap pairing patch must have run. Replace the whole QR-oriented
# card with a single action while preserving Telegram's export/import login-token
# protocol and the official 2FA fallback.
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
    // Short-lived Telegram login token only. Native auth keys never leave Jerkgram.
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
      await pause(diff > FETCH_INTERVAL ? 1e3 * FETCH_INTERVAL : Math.max(250, 1e3 * diff | 0));
      return false;
    } catch(err) {
      switch((err as ApiError).type) {
        case 'SESSION_PASSWORD_NEEDED':
          // Never weaken Telegram 2FA. Use its normal password confirmation card.
          navigate({name: 'password'});
          stopped = true;
          break;
        case 'AUTH_TOKEN_EXPIRED':
          // The normal loop obtains a fresh export token on the next iteration.
          break;
        default:
          console.error('Jerkgram companion pairing error:', err);
          stopped = true;
          break;
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
          Connect notifications to the Telegram account already signed in to Jerkgram.
        </p>
      </div>
      <Button primaryFilled large disabled={!ready()} onClick={connectWithJerkgram}>
        Connect with Jerkgram
      </Button>
      <p class="secondary" style={{'text-align': 'center', 'font-size': '13px', margin: '16px 8px 0'}}>
        No phone number, SMS code or QR scan is requested here.
      </p>
    </AuthCard>
  );
}
''')

# A small runtime owns only Web Push subscription/registration. It deliberately
# bypasses UiNotificationsManager and appDialogsManager so opening the companion
# does not bootstrap chats, media, calls, sidebars or the normal Web K IM.
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
''')

SHELL.write_text(r'''import {ensureJerkgramPushRegistered} from '@lib/jerkgramCompanionPush';

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
  const intro = make('p', 'Notification companion for Jerkgram. After setup, this app can stay closed.');
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
      } catch(error) {
        console.error('Jerkgram push registration failed:', error);
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

  void renderState();
}
''')

# The post-auth entry point is deliberately notification-only. No dynamic import
# of appDialogsManager means its large chat/IM dependency graph is not requested
# by this companion bootstrap.
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
print("  replaced:", SIGN_QR)
print("  replaced:", BOOTSTRAP_IM)
print("  created:", PUSH)
print("  created:", SHELL)
