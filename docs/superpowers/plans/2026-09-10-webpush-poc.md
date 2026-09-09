# Jerkgram Web Push PoC Implementation Plan

## Task 1 — RED contracts for native registration

Create `tests/test_jerkgram_webpush_poc.py` with fixture-based tests against the clean Telegram 12.9.2 source shape. The tests must require:
- a separate `_internal_registerWebPushNotificationToken` helper;
- `tokenType: 10`;
- raw `subscriptionJson` passed as `token`;
- `appSandbox: .boolFalse`;
- empty `secret`;
- preservation of native APNs type 1 and VoIP type 9 registration;
- a public `TelegramEngine.AccountData.registerWebPushNotificationToken` wrapper;
- idempotent/fail-closed patch behavior.

Run only this Python test module and confirm RED before implementing the patcher.

## Task 2 — Implement bounded TelegramCore patcher

Create `scripts/apply_jerkgram_webpush_poc.py` targeting only:
- `submodules/TelegramCore/Sources/TelegramEngine/AccountData/RegisterNotificationToken.swift`
- `submodules/TelegramCore/Sources/TelegramEngine/AccountData/TelegramEngineAccountData.swift`

Use exact anchors from official Telegram iOS 12.9.2 commit `6ad963e5b62d354da79040f388ae2b9132fb17b8`. Refuse to patch if an anchor count differs from exactly one. Do not modify the existing native registration function.

Run the Task 1 tests and confirm GREEN.

## Task 3 — Add materialized-source verifier

Create `scripts/verify_jerkgram_webpush_poc.py` which verifies the generated source contains the Web Push helper/wrapper, raw JSON transport, type 10, empty secret, and intact type 1/type 9 native mappings. It must explicitly reject hex encoding inside the Web Push helper.

Add verifier unit coverage to the same test module and run it.

## Task 4 — Stage static PWA

Create:
- `webpush-poc/site/index.html`
- `webpush-poc/site/manifest.webmanifest`
- `webpush-poc/site/sw.js`

The page registers the service worker, obtains notification permission on a user click, creates/reuses a PushSubscription with Telegram Web K's exact public application-server key, renders the exact serialized subscription JSON, and provides a copy action. No Telegram login, private VAPID key, or backend is allowed.

The service worker handles `push` and displays a notification, with conservative payload parsing and a generic fallback. Notification clicks focus/open the PWA.

Add static tests requiring these properties.

## Task 5 — Do not wire production workflow yet

Do not add the PoC patcher/verifier to the release build workflow and do not add Settings UI until the helper/PWA contracts are green. This prevents Build138-era builds from being changed by an unproven experiment.

The next bounded step after static verification is a tiny debug ingestion path (clipboard or dedicated debug screen) and an HTTPS deployment of the staged PWA. The public `jerkgram/jerkgram.github.io` repository is currently read-only through the connected GitHub installation (`push: false`), so this branch only stages the files; it does not claim deployment.

## Verification before completion

Run:
- `python3 -m unittest tests.test_jerkgram_webpush_poc`
- patch the canonical upstream fixture/tree in a temporary directory;
- `python3 scripts/verify_jerkgram_webpush_poc.py <temporary-tree>`

Do not run Bazel/full app build unless explicitly requested.
