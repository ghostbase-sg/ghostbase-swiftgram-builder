# Jerkgram Push Companion PoC

This PoC deliberately reuses Telegram Web K's existing Web Push stack instead of implementing another Telegram session or another push protocol.

## Product flow

1. A user opens the self-hosted Web K companion once and signs in to Telegram there.
2. The site is added to the iPhone Home Screen and notifications are enabled.
3. Telegram Web K keeps its session and Web Push subscription in browser storage on that device.
4. Telegram sends its normal Web Push payload to the companion service worker.
5. Web K keeps rendering the full notification (`title`, `description`, silent flag, etc.).
6. A default notification tap opens `open.html` on the same origin.
7. `open.html` validates the IDs and hands off to `jerkgram://push/open?...`.
8. Native Jerkgram resolves the target Telegram account + peer namespace + message ID and reuses `openChatWhenReady`.

No message text, sender title, Telegram auth data, Web Push subscription, `p256dh`, or `auth` key is included in the handoff URL.

## Patch Telegram Web K

From this Jerkgram builder checkout:

```bash
python3 webpush-companion/apply_webk_jerkgram_push_v01.py /path/to/tweb
```

The patcher:

- adds `src/lib/serviceWorker/jerkgramPushHandoff.ts`;
- patches only the default notification-click path in `src/lib/serviceWorker/push.ts`;
- copies `public/open.html` and `public/handoff.js`;
- leaves Web K's subscription, `account.registerDevice(token_type=10)`, push decryption, notification rendering, mute/read/delete handling, and non-default actions intact.

Then build/deploy Web K with its normal toolchain.

## Patch native Jerkgram source

```bash
python3 scripts/apply_jerkgram_push_click_bridge_v01.py /path/to/materialized/telegram-ios
python3 scripts/verify_jerkgram_push_click_bridge_v01.py /path/to/materialized/telegram-ios
```

The native patch is intentionally limited to click navigation. It does not modify the existing APNs/VoIP registration path.

## Static tests

```bash
node tests/webpush_handoff_test.mjs
pytest -q tests/test_webk_jerkgram_push_patch.py tests/test_jerkgram_push_click_bridge_v01.py
```

## Runtime acceptance

The PoC is successful only after all of these work with the PWA closed and native Jerkgram backgrounded/closed:

- private message shows sender/title + message text;
- basic group message shows the full notification;
- channel/supergroup message shows the full notification;
- a notification tap opens native Jerkgram rather than another Telegram client;
- multi-account notification opens the correct logged-in Jerkgram account;
- when `msg_id` is present, the exact message is targeted.

The direct-native `token_type=10` experiment is not part of this primary path because Telegram's server-side mapping between API application and VAPID sender key is not public.
