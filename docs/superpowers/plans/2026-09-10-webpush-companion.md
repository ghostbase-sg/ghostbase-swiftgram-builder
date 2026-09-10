# Jerkgram Web Push Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver full Telegram message notifications on iOS through a Home Screen Web Push companion and open the exact chat/message in native Jerkgram when the notification is tapped.

**Architecture:** A Jerkgram PWA creates a Web Push subscription using Telegram Web K's public application-server key. Native Jerkgram receives that subscription through a dedicated `jerkgram://push/register` URL, registers it with Telegram using `account.registerDevice(token_type: 10)` and an empty Telegram-level `secret`, and persists the token for re-registration. Telegram Web Push reaches the PWA service worker directly; the worker renders the server-provided title/description and preserves only account/peer/message identifiers for navigation. Notification taps open a same-origin landing page which hands those identifiers to native Jerkgram through `jerkgram://push/open`, where existing `openChatWhenReady` navigation is reused.

**Tech Stack:** Telegram iOS 12.9.2 Swift/SwiftSignalKit/TelegramCore, Telegram MTProto `account.registerDevice`, Service Worker Push API, Web App Manifest, vanilla JavaScript.

**Spec:** This plan.

## Global Constraints

- Do not alter or remove the existing APNs/VoIP registration path.
- Do not require a Jerkgram backend and do not store Telegram auth keys/sessions in the web companion.
- Web Push registration must use token type `10` and raw JSON token text, never `hexString(token)`.
- Telegram-level `secret` for Web Push is empty; Web Push transport security is provided by the subscription `p256dh`/`auth` keys.
- Register the same Web Push subscription for all active production accounts, with the other active user IDs supplied through `other_uids`.
- Ignore testing-environment accounts in v0.1.
- Set `no_muted` for the PoC so muted chats do not create mandatory user-visible Web Push notifications.
- Never place message text, sender name, auth data, or the subscription token in the notification-click URL; only IDs required for navigation.
- Add a dedicated `jerkgram` URL scheme so an installed original Telegram cannot steal notification clicks.
- PWA must normalize both `{data:{...}}` and direct Telegram Web Push payload shapes.
- Full notification v0.1 means Telegram-provided sender/chat title and message/description text, correct silent behavior, and exact chat/message navigation. Rich media/avatar previews are out of scope.
- No full GitHub Actions app build until static patch/verifier tests pass and the branch is reviewed.

---

### Task 1: Web Push companion

**Files:**
- Create: `webpush-companion/index.html`
- Create: `webpush-companion/app.js`
- Create: `webpush-companion/sw.js`
- Create: `webpush-companion/open.html`
- Create: `webpush-companion/manifest.webmanifest`

**Interfaces:**
- Produces: a raw JSON Web Push subscription containing `endpoint`, `keys.p256dh`, `keys.auth`, and `vapid: true`.
- Produces: native registration URL `jerkgram://push/register?token=<base64url-json>`.
- Produces: native navigation URL carrying only `user`, `kind`, `peer`, `msg`, and optional `thread`.

- [ ] **Step 1:** Add deterministic JavaScript unit-testable helpers for payload normalization, notification presentation, and navigation-data extraction.
- [ ] **Step 2:** Subscribe with `userVisibleOnly: true` and Telegram Web K application-server key.
- [ ] **Step 3:** Transfer the subscription to native Jerkgram only from an explicit user tap.
- [ ] **Step 4:** Handle `push` events, show title/body from Telegram, and fall back safely when fields are absent.
- [ ] **Step 5:** Handle service events (`MESSAGE_DELETED` and `READ_HISTORY`) by closing matching displayed notifications rather than displaying them.
- [ ] **Step 6:** Handle `notificationclick` through same-origin `open.html`, then hand off to `jerkgram://push/open`.

### Task 2: TelegramCore Web Push registration

**Files:**
- Modify via patcher: `submodules/TelegramCore/Sources/TelegramEngine/AccountData/RegisterNotificationToken.swift`
- Modify via patcher: `submodules/TelegramCore/Sources/TelegramEngine/AccountData/TelegramEngineAccountData.swift`
- Create: `scripts/apply_jerkgram_webpush_bridge_v01.py`

**Interfaces:**
- Produces: `registerWebPushNotificationToken(token: String, otherAccountUserIds: [PeerId.Id], excludeMutedChats: Bool) -> Signal<Bool, NoError>`.
- Produces: `unregisterWebPushNotificationToken(token: String, otherAccountUserIds: [PeerId.Id]) -> Signal<Never, NoError>`.

- [ ] **Step 1:** Add failing patch fixture tests proving raw JSON is not hex-encoded and token type is exactly 10.
- [ ] **Step 2:** Add dedicated internal register/unregister functions without modifying `.aps`/`.voip` behavior.
- [ ] **Step 3:** Expose narrow engine wrappers in `TelegramEngineAccountData.swift`.
- [ ] **Step 4:** Return `false` and log the RPC description for Web Push registration errors so `WEBPUSH_*` failures are observable.

### Task 3: Native bridge and exact chat navigation

**Files:**
- Modify via patcher: `submodules/TelegramUI/Sources/AppDelegate.swift`
- Modify via patcher: `Telegram/Telegram-iOS/InfoBazel.plist`
- Modify via patcher: `Telegram/BUILD`

**Interfaces:**
- Consumes: `jerkgram://push/register?token=...` and `jerkgram://push/open?...`.
- Persists: the Web Push token in `UserDefaults` under a Jerkgram-specific key.
- Uses: existing `openChatWhenReady(accountId:peerId:threadId:messageId:...)`.

- [ ] **Step 1:** Register a dedicated `jerkgram` URL scheme without replacing Telegram's existing schemes.
- [ ] **Step 2:** Validate and decode only base64url-encoded subscription JSON with HTTPS endpoint and non-empty `p256dh`/`auth`.
- [ ] **Step 3:** Register the token on all active production accounts and save it only after validation.
- [ ] **Step 4:** Re-register a saved token after launch once active accounts exist.
- [ ] **Step 5:** Parse notification navigation IDs, select the target account by Telegram `user_id`, construct the correct CloudUser/CloudGroup/CloudChannel `PeerId`, and invoke `openChatWhenReady` with the `MessageId` and optional thread ID.
- [ ] **Step 6:** Reject malformed/oversized deep links without crashing or passing them to Telegram's normal URL parser.

### Task 4: Verifier and static regression tests

**Files:**
- Create: `scripts/verify_jerkgram_webpush_bridge_v01.py`
- Create: `tests/test_jerkgram_webpush_bridge_v01.py`
- Create: `tests/webpush_companion_test.mjs`

**Interfaces:**
- Verifies the materialized Telegram source and standalone web helper behavior.

- [ ] **Step 1:** Assert token type 10 exists only in the Jerkgram Web Push path and the raw token is passed unchanged.
- [ ] **Step 2:** Assert existing APNs type 1 and VoIP type 9 mappings remain present.
- [ ] **Step 3:** Assert the dedicated `jerkgram` URL scheme is present exactly once in each generated plist/build template owner.
- [ ] **Step 4:** Test payload normalization for direct and `{data:...}` payloads, private chats, basic groups, channels/supergroups, silent messages, and missing text.
- [ ] **Step 5:** Test that navigation URLs never contain title/body/message content.
- [ ] **Step 6:** Run Python and Node static tests; do not trigger a full app build yet.

### Task 5: Runtime acceptance

**Files:** none.

- [ ] **Step 1:** Deploy `webpush-companion/` under HTTPS and add it to the iPhone Home Screen.
- [ ] **Step 2:** Tap Connect Jerkgram and confirm native registration reports success rather than a `WEBPUSH_*` RPC error.
- [ ] **Step 3:** Fully close the PWA and background/close Jerkgram, then send a private text message from another account; require sender/title + message text on Lock Screen/Notification Center.
- [ ] **Step 4:** Repeat for a basic group and a supergroup/channel.
- [ ] **Step 5:** Tap each notification and require native Jerkgram to open the correct account, chat, and message.
- [ ] **Step 6:** Only after runtime acceptance, decide whether to integrate the patcher into the normal build chain.
