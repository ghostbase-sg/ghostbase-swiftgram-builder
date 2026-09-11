# Jerkgram Web Push Tap Fallback Design

## Goal

Make taps on Jerkgram Notifications Web Push reliably open the exact account/chat/message in native Jerkgram on iOS, including the WebKit failure mode where tapping a notification merely foregrounds the Home Screen PWA at its start URL.

## Current evidence

The original working click path was intentionally simple:

`notificationclick -> clients.openWindow(open.html?...push ids...) -> open.html -> window.location.href = jerkgram://push/open?...`

The later sender/message-text formatter changed notification presentation only. It did not change that click path. Therefore sender/message rendering is not treated as the root cause of the navigation regression.

Real-device testing shows a distinct iOS/WebKit failure mode: after tapping a push, Jerkgram Notifications is foregrounded at its normal start screen and native Jerkgram is never handed the push URL. Native Jerkgram's `jerkgram://push/open` handler is already proven separately, so the unresolved failure is before native dispatch.

## Architecture

Keep all existing fast paths:

1. `NotificationOptions.navigate` may navigate directly to the same-origin landing page.
2. `notificationclick` may execute and open/navigate the landing page.
3. The landing page may immediately hand off to `jerkgram://push/open`.

Add one final root-screen resolver for the WebKit case where neither path reaches the landing page and iOS only foregrounds the PWA.

At notification creation time, persist a small local record for each live notification containing:

- a stable notification identity derived from the push/account/chat/message fields;
- the validated native handoff URL (`jerkgram://push/open?...`);
- an expiry timestamp;
- enough metadata to match the record to a still-live notification without storing message text.

The root PWA bootstrap maintains a snapshot of live notifications using `ServiceWorkerRegistration.getNotifications()`. When the PWA becomes visible after a notification tap, it compares the current live-notification identities against the previously persisted snapshot.

If exactly one previously-live notification disappeared and exactly one unexpired handoff record matches it, the resolver opens that native URL. If the result is ambiguous, stale, malformed, or there is no unique match, it does nothing.

## Safety and privacy constraints

- Never guess between multiple candidate notifications.
- Never open a different account/chat/message as a fallback.
- Persist no message body, sender name, media caption, endpoint, push keys, or Telegram auth material.
- Accept only validated `jerkgram://push/open` URLs with the existing allowlist: `kind`, `peer`, `user`, `msg`, `thread`.
- Expire resolver records quickly and delete consumed records.
- Keep the resolver same-origin and local-only; no server/VPS is introduced.

## Failure behavior

If direct navigation works, the resolver stays inert.

If WebKit foregrounds only the PWA root, the resolver opens native Jerkgram only when the disappeared-notification match is unique.

If the resolver cannot prove which notification was tapped, Jerkgram Notifications remains open instead of opening a wrong chat.

## Testing

Add deterministic unit/static coverage for:

- notification identity generation;
- persistence without message text;
- snapshot comparison with exactly one disappeared notification;
- zero disappeared notifications;
- multiple disappeared notifications;
- expired records;
- malformed/non-Jerkgram URLs;
- consumed-record deletion;
- package inclusion of the resolver/bootstrap.

Then run the existing companion static tests, Web K typecheck, Vite build, notification-only package verifier, and artifact upload.

Runtime acceptance remains real-device only: with Jerkgram Notifications closed, receive two distinguishable pushes, tap one, and verify native Jerkgram opens the exact account/chat/message. Repeat with the PWA already open and with native Jerkgram already open.
