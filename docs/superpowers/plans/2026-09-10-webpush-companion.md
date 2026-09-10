# Jerkgram Web Push Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver full Telegram message notifications through an iOS Home Screen Web Push companion, with one-tap authorization from an already logged-in Jerkgram account and exact native chat/message navigation on notification tap.

**Architecture:** The companion is a separately hosted, patched Telegram Web K instance used as a background push agent, not as the user's primary Telegram UI. It keeps its own Telegram authorization and Web Push state only in its own browser origin. Pairing uses Telegram's official `auth.exportLoginToken` / `auth.acceptLoginToken` flow: Web K creates the short-lived QR login token, opens `jerkgram://push/authorize`, native Jerkgram asks for confirmation and approves it using the already logged-in account. Web K then keeps its normal `token_type=10` registration and notification payload handling. Notification taps are redirected to `jerkgram://push/open` and native Jerkgram reuses `openChatWhenReady`.

**Tech Stack:** Telegram iOS 12.9.2 Swift/SwiftSignalKit/TelegramCore, Telegram Web K, MTProto auth login-token transfer, Service Worker Push API, Web App Manifest, vanilla JavaScript handoff.

**Spec:** This plan.

## Global Constraints

- Do not alter or remove Jerkgram's existing APNs/VoIP registration path.
- Do not copy native MTProto auth keys, session files, phone numbers, SMS codes, or 2FA secrets into the companion.
- Do not require manual phone/code login in the companion for the normal pairing path.
- Pairing must use a short-lived `auth.exportLoginToken` approved by native Jerkgram through `auth.acceptLoginToken`.
- Native Jerkgram must require an explicit confirmation before approving a companion login token.
- The companion must be hosted on an origin separate from `web.telegram.org`; it must never read, overwrite, or depend on the user's ordinary Telegram Web storage/service worker/subscription.
- Keep Telegram Web K's normal Web Push registration (`token_type=10`) and payload processing intact; patch only companion UX and notification-click routing.
- Never place message text, sender name, Telegram authorization data, or Web Push subscription secrets in notification-click URLs; only IDs required for navigation.
- Add/use the dedicated `jerkgram` URL scheme so original Telegram cannot steal companion handoffs.
- Full notification v0.1 means Telegram-provided sender/chat title and message/description text plus exact account/chat/message navigation. Rich media/avatar previews are out of scope.
- The companion is a setup/status agent. A full second Telegram chat UI is not part of the intended product surface, even though Web K supplies the underlying engine.
- Do not trigger the full macOS iOS app build until companion Linux CI and bounded patcher tests are green.

---

### Task 1: Preserve Web K full Web Push and redirect taps

**Files:**
- Create: `webpush-companion/handoff.js`
- Create: `webpush-companion/open.html`
- Create: `webpush-companion/apply_webk_jerkgram_push_v01.py`
- Test: `tests/webpush_handoff_test.mjs`
- Test: `tests/test_webk_jerkgram_push_patch.py`

- [x] Preserve Web K's existing push receive/decrypt/showNotification behavior.
- [x] Extract only `user_id`, `from_id/chat_id/channel_id`, `msg_id`, and optional `top_msg_id` for native navigation.
- [x] Redirect default notification taps to same-origin `open.html`, then `jerkgram://push/open`.
- [x] Keep Telegram Web K's existing notification action-button handler untouched.
- [x] Cover private chats, groups, channels/supergroups and topics in deterministic handoff tests.

### Task 2: One-tap companion pairing through Jerkgram

**Files:**
- Create: `webpush-companion/apply_webk_jerkgram_pairing_v01.py`
- Create: `scripts/apply_jerkgram_push_pairing_bridge_v01.py`
- Test: `tests/test_webk_jerkgram_pairing_v01.py`
- Test: `tests/test_jerkgram_push_pairing_bridge_v01.py`

- [x] Reuse Web K `SignQRCard`'s current short-lived `auth.exportLoginToken` value.
- [x] Add `Connect with Jerkgram`, opening `jerkgram://push/authorize?token=<base64url>`.
- [x] Validate scheme/host/path, URL size, URL-safe base64 alphabet and decoded token size natively.
- [x] Select the primary currently logged-in Jerkgram account.
- [x] Show a native confirmation explaining that a separate companion Telegram session will be created.
- [x] Approve with Telegram iOS's existing `approveAuthTransferToken`, which calls `auth.acceptLoginToken`.
- [x] Keep malformed pairing links out of Telegram's generic URL parser.
- [ ] Runtime-check the foreground/background handoff: after native approval, Web K must observe login success when the user returns to the PWA.
- [ ] Replace the normal post-auth Web K chat surface with a minimal Jerkgram Notifications status surface after runtime pairing is proven.

### Task 3: Native notification click bridge

**Files:**
- Create: `scripts/apply_jerkgram_push_click_bridge_v01.py`
- Create: `scripts/verify_jerkgram_push_click_bridge_v01.py`
- Test: `tests/test_jerkgram_push_click_bridge_v01.py`

- [x] Add the dedicated `jerkgram` URL scheme without replacing Telegram's existing schemes.
- [x] Parse only validated `user/kind/peer/msg/thread` identifiers.
- [x] Map user/basic-group/channel IDs to the appropriate Telegram `PeerId` namespace.
- [x] Select the target logged-in account by Telegram `user_id` when supplied.
- [x] Reuse `openChatWhenReady` for cold-start-safe exact message navigation.
- [x] Reject malformed/oversized deep links without passing them to Telegram's normal parser.

### Task 4: Companion build and packaging verification

**Files:**
- Create/update: `.github/workflows/webpush-companion-poc.yml`

- [x] Run Node and Python bounded tests on Linux only.
- [x] Pin the tested Telegram Web K commit.
- [x] Apply both Web K push-handoff and one-tap-pairing patches before typecheck/build.
- [x] Run Web K TypeScript typecheck and Vite production build.
- [x] Respect Web K `copyPublicDir:false`; explicitly package only Jerkgram-owned `open.html` and `handoff.js` after build.
- [ ] Require a completely green workflow and upload the deployable `dist` artifact.

### Task 5: Runtime acceptance on iPhone

**Files:** none.

- [ ] Host the companion `dist` over HTTPS on an origin not equal to `web.telegram.org` and add it to the iPhone Home Screen.
- [ ] Start pairing from the companion, approve once inside already logged-in Jerkgram, and confirm no phone/code/password entry is required in the companion.
- [ ] Enable Web Push and confirm the companion has an active Telegram Web Push registration.
- [ ] Background/close both surfaces and send a private text from another account; require sender/title and message body on Lock Screen/Notification Center.
- [ ] Repeat for basic group and supergroup/channel.
- [ ] Tap each notification and require native Jerkgram to open the correct logged-in account, peer, topic when applicable, and message.
- [ ] Confirm a separate existing `web.telegram.org` login remains logged in and its storage/push behavior is unchanged.
- [ ] Only after all acceptance checks pass, integrate the native patchers into the normal Jerkgram build chain.
