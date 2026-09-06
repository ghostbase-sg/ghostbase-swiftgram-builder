# Blocked Reactions, Settings, and Music Runtime Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make blocked-user reactions/activity/navigation consistent, localize and relayout the blocked-user settings, and restore a native translucent profile music overlay.

**Architecture:** Add late fail-closed source patches after the existing v1.0W chain. Keep storage untouched; filter at the owners where blocked-peer state meets presentation/navigation state. Settings use Telegram presentation language and item-list rows. Music repair removes custom replacement visuals while preserving Telegram overlay owners and controls.

**Tech Stack:** Python source patchers/verifiers, Swift Telegram iOS 12.9.2 owners, GitHub Actions remote build.

**Spec:** `docs/superpowers/specs/2026-09-06-blocked-reactions-settings-music-design.md`

## Global Constraints
- Telegram base: 12.9.2.
- Do not use `dev/build124-sequential`.
- Do not restart the port.
- No local Bazel/Xcode build.
- Fail closed on missing/ambiguous source anchors.
- Preserve native Telegram geometry and behavior outside the requested repairs.

---

### Task 1: Blocked reaction consistency

**Files:**
- Create: `scripts/apply_ghostbase_build133_blocked_reactions.py`
- Create: `scripts/verify_ghostbase_build133_blocked_reactions.py`
- Modify: `scripts/apply_all_ghostbase_patches_only.sh`

**Interfaces:**
- Consumes: the post-v1.0W Telegram 12.9.2 source tree and existing blocked-user preference/state.
- Produces: filtered user-facing reaction state with no blocked peer contribution.

- [ ] Locate the exact presentation owner(s) where reaction peers/counts and blocked-peer state meet.
- [ ] Add verifier assertions for sole-blocked and mixed-reactor invariants; verify they fail before repair.
- [ ] Implement the minimal fail-closed source patch at those owners.
- [ ] Run Python syntax/static verifier checks and verify they pass.
- [ ] Commit the isolated reaction repair.

### Task 2: Blocked activity and navigation

**Files:**
- Create: `scripts/apply_ghostbase_build133_blocked_activity_navigation.py`
- Create: `scripts/verify_ghostbase_build133_blocked_activity_navigation.py`
- Modify: `scripts/apply_all_ghostbase_patches_only.sh`

**Interfaces:**
- Consumes: post-filter message/activity targets and existing hidden-message predicate.
- Produces: no blocked-only chat-list activity and no navigation control without a visible target.

- [ ] Locate the exact chat-list unseen reaction/mention and `ChatControllerNavigateToMessage` owner paths.
- [ ] Add verifier assertions for blocked-only activity and empty post-filter navigation targets; verify they fail before repair.
- [ ] Patch activity generation and navigation target selection independently, with fail-closed anchors.
- [ ] Run Python syntax/static verifier checks and verify they pass.
- [ ] Commit the isolated activity/navigation repair.

### Task 3: Blocked settings localization and layout

**Files:**
- Create: `scripts/apply_ghostbase_build133_blocked_settings.py`
- Create: `scripts/verify_ghostbase_build133_blocked_settings.py`
- Modify: `scripts/apply_all_ghostbase_patches_only.sh`

**Interfaces:**
- Consumes: `PresentationStrings.baseLanguageCode`, existing blocked-message/reaction preference keys.
- Produces: localized separate blocked-user section using Telegram item-list switch rows.

- [ ] Add verifier assertions rejecting Cyrillic-only blocked labels, `EDIT HISTORY` placement, and custom fixed-width switch rows; verify they fail on the broken generated source.
- [ ] Add English-fallback/Russian localization helper based on `baseLanguageCode`.
- [ ] Move the two toggles into a separate localized section and render with Telegram `ItemListSwitchItem`-style rows.
- [ ] Run Python syntax/static verifier checks and verify they pass.
- [ ] Commit the isolated settings repair.

### Task 4: Profile music overlay continuity

**Files:**
- Create: `scripts/apply_ghostbase_build133_music_overlay.py`
- Create: `scripts/verify_ghostbase_build133_music_overlay.py`
- Modify: `scripts/apply_all_ghostbase_patches_only.sh`

**Interfaces:**
- Consumes: native `OverlayAudioPlayerController`, `OverlayAudioPlayerControllerNode`, `OverlayAudioPlayerControlsNode`.
- Produces: native controls/geometry with subtle translucent material and no cloned/opaque replacement backdrop.

- [ ] Diff custom music patch anchors against the three Telegram owners.
- [ ] Add verifier assertions rejecting the cloned profile backdrop/large opaque replacement surface; verify they fail before repair.
- [ ] Remove only the custom replacement visual layer and preserve native controls/geometry.
- [ ] Apply only a subtle material/translucency adjustment where the native owner exposes it safely.
- [ ] Run Python syntax/static verifier checks and verify they pass.
- [ ] Commit the isolated music repair.

### Task 5: Chain and remote verification

**Files:**
- Modify: `scripts/apply_all_ghostbase_patches_only.sh`
- Modify/add final-source verifier only if the existing verifier requires explicit Build133 registration.

**Interfaces:**
- Consumes: four independently verified repair patches.
- Produces: deterministic patch-chain through Build133, ready for remote build/runtime validation.

- [ ] Append the four Build133 patches after v1.0W in dependency order: reactions, activity/navigation, settings, music.
- [ ] Append their verifiers after the patches.
- [ ] Check shell/Python syntax and patch-chain ordering without running Bazel/Xcode.
- [ ] Trigger/request remote build only after static/source verification is green.
- [ ] Runtime-test all eight acceptance cases from the spec.
