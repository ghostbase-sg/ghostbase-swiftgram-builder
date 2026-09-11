# Jerkgram Web Push Tap Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the original known-good notification tap path and add a safe local resolver for the iOS/WebKit case where tapping a Web Push only foregrounds the Jerkgram Notifications start screen.

**Architecture:** Keep the proven `notificationclick -> openWindow(open.html) -> jerkgram://push/open` fast path from the early companion build. Remove the later `NotificationOptions.navigate`/service-worker navigation interception that regressed real-device behavior. Add a local-only resolver that snapshots live notifications when they are shown and, on a root PWA launch, opens native Jerkgram only when exactly one previously-live notification has disappeared and exactly one validated handoff record matches it.

**Tech Stack:** Telegram Web K service worker, JavaScript, CacheStorage, ServiceWorkerRegistration.getNotifications(), Python patchers/tests, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-11-webpush-tap-fallback-design.md`

## Global Constraints

- Keep Telegram Web K pinned to `e9428f2a90f73d750f16a0b85817820516466364`.
- Do not modify native Jerkgram/Build140 for this web-only fix.
- Never guess between multiple candidate notifications.
- Never persist message body, sender name, caption, Web Push endpoint/keys, or Telegram auth material.
- Only open validated `jerkgram://push/open` URLs with `kind`, `peer`, `user`, `msg`, `thread`.
- Real-device runtime remains the final acceptance gate.

---

### Task 1: Pure notification identity and resolver logic

**Files:**
- Create: `webpush-companion/tap-fallback.js`
- Create: `tests/webpush_tap_fallback_test.mjs`

**Interfaces:**
- Produces: `buildJerkgramTapIdentity(push) -> string|null`
- Produces: `findUniqueDisappearedTap(previousIds, currentIds, records, now) -> {id,url}|null`
- Produces: `normalizeJerkgramOpenUrl(value) -> string|null`

- [ ] **Step 1: Write failing Node tests** covering stable identities, one disappeared notification, zero/multiple disappeared notifications, expired records, malformed URLs, and records containing only id/url/expiry.
- [ ] **Step 2: Commit the tests alone and verify GitHub static-tests fails because `tap-fallback.js` is missing.**
- [ ] **Step 3: Add the minimal pure helper implementation.**
- [ ] **Step 4: Run/verify static tests green.**

### Task 2: Restore proven fast path and persist tap state in the service worker

**Files:**
- Modify: `webpush-companion/apply_webk_jerkgram_push_v01.py`
- Modify: `tests/test_webk_jerkgram_push_patch.py`

**Interfaces:**
- Consumes: `buildJerkgramTapIdentity`, `normalizeJerkgramOpenUrl`
- Produces runtime CacheStorage state under `jerkgram-push-tap-v1` with a live snapshot and per-notification handoff records.

- [ ] **Step 1: Update the patcher test first** to require the original simple click branch, absence of `NotificationOptions.navigate`, absence of service-worker fetch interception, and presence of tap-state persistence after `showNotification`.
- [ ] **Step 2: Verify the updated test fails on the current patcher.**
- [ ] **Step 3: Modify the patcher minimally:** restore `notificationclick -> clients.openWindow(open.html...)`, stop patching `index.service.ts`, stop injecting `navigate`, copy/import `tap-fallback.js`, and after a successful `showNotification` persist `{id,url,expiresAt}` plus the current live-id snapshot without message text.
- [ ] **Step 4: Verify patcher tests green.**

### Task 3: Root-screen fallback resolver and packaging

**Files:**
- Create: `webpush-companion/push-tap-resolver.js`
- Modify: `webpush-companion/apply_webk_jerkgram_push_v01.py`
- Modify: `webpush-companion/package_webk_dist_v01.py`
- Modify: `tests/test_webk_companion_package_v01.py`
- Modify: `tests/test_webk_jerkgram_push_patch.py`

**Interfaces:**
- Root resolver reads the stored snapshot and current `registration.getNotifications()` values, derives current ids with `buildJerkgramTapIdentity`, and navigates to native only for one unambiguous disappeared id.

- [ ] **Step 1: Add failing static/package assertions** for `tap-fallback.js`, `push-tap-resolver.js`, index inclusion, consumed-record deletion, and no legacy `push-open-bootstrap.js` requirement.
- [ ] **Step 2: Verify red.**
- [ ] **Step 3: Implement the root resolver** with one-shot launch/visibility checks, record expiry, validated URL handling, consumed-record deletion, and snapshot replacement with the current live set.
- [ ] **Step 4: Update package allowlist/required assets and remove the legacy bootstrap asset from the runtime contract.**
- [ ] **Step 5: Verify static/package tests green.**

### Task 4: Full CI and handoff

- [ ] **Step 1: Run the full branch workflow.**
- [ ] **Step 2: Require `static-tests` success.**
- [ ] **Step 3: Require Web K typecheck, Vite build, package, verifier, and artifact upload success.**
- [ ] **Step 4: Only after full green, give the user the new `JERKGRAM_BUILDER_COMMIT` for the Pages workflow.**
- [ ] **Step 5: Real-device acceptance:** receive two distinguishable pushes, tap one with PWA closed, verify exact native account/chat/message; repeat with PWA open and native Jerkgram already open.
