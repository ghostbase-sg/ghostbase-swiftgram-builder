# Jerkgram Web Push Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver full Telegram text notifications on iOS through a Home Screen Jerkgram Push Companion and open the exact account/chat/message in native Jerkgram when a notification is tapped.

**Architecture:** The primary path is a narrowly patched self-hosted Telegram Web K companion. Web K keeps its own Telegram web session in browser storage on the iPhone and keeps its known API/VAPID pairing, so Telegram can deliver its normal Web Push payload directly to the service worker. The service worker keeps Web K's existing full notification rendering, but default notification taps are handed to a same-origin landing page and then to a dedicated `jerkgram://push/open` deep link in native Jerkgram. A direct native `token_type=10` registration bridge remains an experimental diagnostic only because the Telegram backend's mapping between API application and VAPID sender key is not public.

**Tech Stack:** Telegram Web K Service Worker/Push API, Telegram iOS 12.9.2 Swift/SwiftSignalKit, Python source patchers/verifiers, vanilla JavaScript.

**Spec:** This plan.

## Global Constraints

- Do not alter or remove Jerkgram's existing APNs/VoIP registration path.
- Do not store Telegram auth keys/sessions on a Jerkgram server. The companion session remains in Web K's local browser storage.
- Keep Web K's own Web Push subscription and `account.registerDevice(token_type: 10)` machinery unchanged in the primary path.
- Never place message text, sender/chat title, auth data, subscription data, or Web Push keys in a click URL. Only account/peer/message/thread identifiers may cross the PWA -> native handoff.
- Add a dedicated `jerkgram` URL scheme. Do not use `tg://` or `telegram://` for companion clicks because another installed Telegram client may own them.
- Full notification v0.1 means Telegram-provided sender/chat title plus text/description, correct silent behavior, and exact account/chat/message navigation. Rich avatar/media thumbnails are out of scope.
- Preserve Telegram Web K handling for encrypted push payloads, read-history cleanup, deleted-message cleanup, notification actions, and muted/silent behavior.
- Ignore non-message notification types for deep navigation when they do not contain a resolvable peer; they may fall back to opening Jerkgram normally.
- No full GitHub Actions app build until patcher/verifier tests pass.

---

### Task 1: Pure notification handoff helper

**Files:**
- Create: `webpush-companion/handoff.js`
- Create: `tests/webpush_handoff_test.mjs`

**Interfaces:**
- `buildJerkgramHandoffData(push)` -> `{user, kind, peer, msg?, thread?}` or `null`.
- `buildLandingUrl(scope, data)` -> same-origin HTTPS `open.html` URL containing IDs only.
- `buildNativeUrl(data)` -> `jerkgram://push/open?...` containing IDs only.

- [ ] Write tests for private user, basic group, channel/supergroup, topic/top message, missing peer, malformed IDs, and leakage of title/body.
- [ ] Implement only enough parsing to satisfy the tests.

### Task 2: Web K patch

**Files:**
- Create: `webpush-companion/apply_webk_jerkgram_push_v01.py`
- Create: `webpush-companion/open.html`
- Create: `webpush-companion/README.md`
- Test: `tests/test_webk_jerkgram_push_patch.py`

**Interfaces:**
- Consumes a Telegram Web K checkout containing `src/lib/serviceWorker/push.ts`.
- Replaces only the default notification-click branch after Web K has already parsed/decrypted the Telegram push.
- Produces a same-origin landing URL, then a dedicated native Jerkgram deep link.

- [ ] Fixture-test the exact Web K click-handler anchor before patching.
- [ ] Preserve Web K's existing notification rendering and non-default actions.
- [ ] On default click, extract only `user_id`, `custom.from_id/chat_id/channel_id`, `custom.msg_id`, and `custom.top_msg_id`.
- [ ] Use `clients.openWindow()` for the same-origin landing page.
- [ ] Landing page attempts the native deep link and exposes a visible fallback button.

### Task 3: Native Jerkgram click bridge

**Files:**
- Create: `scripts/apply_jerkgram_push_click_bridge_v01.py`
- Modify through patcher: `submodules/TelegramUI/Sources/AppDelegate.swift`
- Modify through patcher: `Telegram/Telegram-iOS/InfoBazel.plist`
- Modify through patcher: `Telegram/BUILD`
- Test: `tests/test_jerkgram_push_click_bridge_v01.py`

**Interfaces:**
- Consumes `jerkgram://push/open?user=<telegram-user-id>&kind=<user|chat|channel>&peer=<id>&msg=<id>&thread=<id>`.
- Uses existing `openChatWhenReady(accountId:peerId:threadId:messageId:storyId:alwaysKeepMessageId:)`.

- [ ] Add the `jerkgram` URL scheme without replacing existing Telegram schemes.
- [ ] Intercept only `scheme=jerkgram`, `host=push`, `path=/open` before normal Telegram URL handling.
- [ ] Validate query length and numeric values; reject malformed links without crashing.
- [ ] Resolve `user` against `activeAccountContexts` to choose the correct logged-in account.
- [ ] Map `kind=user` -> CloudUser, `chat` -> CloudGroup, `channel` -> CloudChannel.
- [ ] Build optional Cloud `MessageId` and call `openChatWhenReady(... alwaysKeepMessageId: true)`.

### Task 4: Static verifier

**Files:**
- Create: `scripts/verify_jerkgram_push_click_bridge_v01.py`

- [ ] Verify `jerkgram` scheme ownership in both plist/build-template owners.
- [ ] Verify the deep-link parser exists once and calls `openChatWhenReady`.
- [ ] Verify existing `telegram`, `tg`, APS token type 1, and VoIP token type 9 markers remain unchanged.
- [ ] Run Python/Node static tests. Do not trigger a full app build.

### Task 5: Optional direct type-10 diagnostic

**Files:**
- Separate patcher/tests only if the primary Web K companion works or a runtime experiment is explicitly useful.

- [ ] Never integrate this path into normal builds by default.
- [ ] If tested, register raw Web Push JSON as token type 10 and record the exact RPC result.
- [ ] Treat successful registration without delivery as evidence of an API/VAPID sender-key mismatch, not as success.

### Task 6: Runtime acceptance

**Files:** none.

- [ ] Host the patched Web K companion under HTTPS and log into Telegram once in the companion.
- [ ] Add it to the iPhone Home Screen and enable notifications.
- [ ] Close the web companion and background/close native Jerkgram.
- [ ] Send a private text message and require full sender/title + message text in the notification.
- [ ] Repeat for a basic group and a supergroup/channel.
- [ ] Tap each notification and require native Jerkgram to open the correct account, peer, and exact message.
- [ ] Only after runtime acceptance integrate the native click bridge into the normal Jerkgram patch chain.
