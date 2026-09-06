# Jerkgram Blocked Reactions, Settings, and Music Runtime Repair Design

## Goal
Repair the 2026-09-06 runtime regressions without changing unrelated Telegram 12.9.2 behavior.

## Blocked-user reactions
When `Hide Blocked Reactions` is enabled, a blocked peer does not contribute to user-facing reaction state. If the blocked peer is the only reactor for a reaction value, the reaction disappears. If allowed peers also reacted with that value, only allowed peers remain and the visible count is recomputed. The same filtered model must feed the message reaction surface and reaction-detail surface.

## Activity and navigation
Reaction or mention activity whose only source/target is hidden by the blocked-user filter must not produce chat-list activity, unread/unseen navigation state, or a jump control. Navigation UI exists only when at least one post-filter target message is visible and navigable.

## Settings
The blocked-user switches live in their own section, not `EDIT HISTORY`.

English:
- `BLOCKED USERS`
- `Hide Blocked Messages`
- `Hide Blocked Reactions`

Russian:
- `ЗАБЛОКИРОВАННЫЕ`
- `Скрывать сообщения заблокированных`
- `Скрывать реакции заблокированных`

Language is selected from Telegram presentation data using `PresentationStrings.baseLanguageCode`, with English as canonical fallback. The rows use Telegram item-list switch items; no custom fixed-width label/switch layout is allowed.

## Profile music overlay
Keep native `OverlayAudioPlayerController`, `OverlayAudioPlayerControllerNode`, and `OverlayAudioPlayerControlsNode` geometry and controls. The real profile remains visually continuous behind the overlay. Do not build a cloned profile backdrop or a large opaque replacement card. Jerkgram styling is limited to a subtle translucent/material layer and must not replace native seek/play/playlist behavior.

## Owner policy
Do not patch TelegramCore reaction storage merely because it owns `ReactionsMessageAttribute`. Install blocked filtering at the lowest owner where both the relevant reaction/activity model and blocked-peer state are available. Reaction detail, chat-list activity, and jump navigation are separate owners when Telegram routes them independently.

## Patch-chain policy
- Repair patches run after the existing v1.0W chain.
- Missing or ambiguous anchors fail closed.
- Patches are semantically idempotent.
- Each repair has a source verifier.
- No local Bazel/Xcode build is used as patch verification.

## Runtime acceptance matrix
1. Blocked peer is sole reactor -> no reaction bubble/count/detail entry.
2. Blocked + allowed peers share a reaction -> allowed peers/count remain.
3. Blocked peer reaction/mention only -> no chat-list activity indicator.
4. Hidden target only -> no jump button.
5. Telegram EN -> blocked section/rows are English.
6. Telegram RU -> blocked section/rows are Russian.
7. Long labels never overlap the switch.
8. Music overlay keeps native controls/geometry and profile continuity with only subtle translucency.
