#!/usr/bin/env bash
set -euo pipefail
GHOSTBASE_BUILDER_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export USE_BAZEL_VERSION="${USE_BAZEL_VERSION:-8.4.2}"
BAZEL_BIN="${BAZEL_BIN:-bazelisk}"
GHOSTBASE_BAZEL_TARGET="${GHOSTBASE_BAZEL_TARGET:-//Telegram:Telegram}"
GHOSTBASE_PROBE_ONLY="${GHOSTBASE_PROBE_ONLY:-0}"

SIGN_DIR="${RUNNER_TEMP:-/tmp}/signing"
mkdir -p "$SIGN_DIR"

cd work/swiftgram-src
export GHOSTBASE_SOURCE_ROOT="$PWD"

EXPECTED_TELEGRAM_COMMIT="6ad963e5b62d354da79040f388ae2b9132fb17b8"
ACTUAL_TELEGRAM_COMMIT="$(git rev-parse HEAD)"

echo "== Telegram 12.9.2 source gate =="
echo "Expected: $EXPECTED_TELEGRAM_COMMIT"
echo "Actual:   $ACTUAL_TELEGRAM_COMMIT"

if [ "$ACTUAL_TELEGRAM_COMMIT" != "$EXPECTED_TELEGRAM_COMMIT" ]; then
  echo "ERROR: build script received an unexpected Telegram source"
  false
fi

echo "== clean stale GhostBase final artifacts =="
rm -rf ghostbase-final
mkdir -p ghostbase-final

echo
echo "== apply/verify GhostBase Edit History v0.9A patch =="
if grep -q "Version: v0.9A" submodules/SettingsUI/Sources/GhostBase/GhostBaseSettingsController.swift 2>/dev/null && grep -q "GhostBase v0.9A edit history context action" submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift 2>/dev/null; then
  echo "GhostBase v0.9A already applied; skip duplicate patch"
else
  # MARK: GhostBase clean source before v0.9F.3-lite
  echo "== clean source before GhostBase patch =="
  git reset --hard HEAD
  rm -rf submodules/SettingsUI/Sources/GhostBase
  rm -f submodules/TelegramCore/Sources/SyncCore/GhostBaseMessageAttribute.swift
  rm -f .GHOSTBASE_KEEP_DO_NOT_DELETE
  echo "== source status before GhostBase patch =="
  git status --short | head -40

  python3 ../../scripts/apply_ghostbase_v10q_sh2_ot2_combined.py
fi

echo
echo "== apply GhostBase v1.0R settings split =="
python3 ../../scripts/apply_ghostbase_v10r_menu.py

echo
echo "== apply GhostBase v1.0S =="
python3 ../../scripts/apply_ghostbase_v10s_public_controls.py

echo
echo "== apply GhostBase v1.0S post share fix =="
python3 ../../scripts/apply_ghostbase_v10s_post_share_fix.py
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10t.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10t_style_settings.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10t_style_menu.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10t_style_runtime.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10u.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10u_style_preview.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10u_appearance.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10w_voice_cleanup.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10w_forward_official.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10w_hide_phone_settings.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10w_metadata.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10w_native_style_page.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10x_runtime_fixes.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10x_copy_peer_id.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10w_generated_source.py"

echo
echo "== apply GhostBase v1.0V =="

echo "== verify GhostBase v1.0R settings split =="
grep -nE   'GhostBase v1.0R Settings Split|GhostBaseHome|GhostBaseGhostMode|GhostBaseMessages|GhostBaseProtectedContent|GhostBaseMediaStories|GhostBaseAppearance|GhostBaseDebugResearch|GhostBaseAbout'   submodules/SettingsUI/Sources/GhostBase/GhostBaseSettingsController.swift

echo "== verify GhostBase source patch =="
grep -RInE 'case ghostbase|openSettings\(\.ghostbase\)|case \.ghostbase|GhostBase|Telegram ID|KeychainFix' \
  submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoScreen.swift \
  submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoSettingsItems.swift \
  submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoScreenSettingsActions.swift


echo "== Build113 unsigned ESign-ready mode =="
echo "CI certificate/provisioning secrets are intentionally not required"

echo "== bazelisk / bazel =="
which "$BAZEL_BIN"
"$BAZEL_BIN" --version || true

echo
echo "== init bazel rule submodules =="
git submodule sync --recursive
git submodule update --init --recursive --depth 1 \
  build-system/bazel-rules/apple_support \
  build-system/bazel-rules/rules_apple \
  build-system/bazel-rules/rules_swift \
  build-system/bazel-rules/rules_xcodeproj \
  build-system/bazel-rules/sourcekit-bazel-bsp

echo
echo "== init source submodules =="
git submodule update --init --recursive --depth 1 \
  submodules/LottieCpp/lottiecpp \
  submodules/TgVoipWebrtc/tgcalls \
  submodules/rlottie/rlottie \
  third-party/dav1d/dav1d \
  third-party/libvpx/libvpx \
  third-party/td/td \
  third-party/webrtc/webrtc

echo
echo "== create build configuration repo =="
rm -rf build-input/configuration-repository
mkdir -p build-input
cp -R build-system/example-configuration build-input/configuration-repository

printf '%s\n' 'module(name = "build_configuration", version = "0.0.0")' \
  > build-input/configuration-repository/MODULE.bazel

cat >> build-input/configuration-repository/variables.bzl <<'EOF'

# Added by GhostBase builder
telegram_bazel_path = "."
telegram_use_xcode_managed_codesigning = False

# Swiftgram config placeholder for BuildConfig
sg_config = "{}"
EOF


echo
echo "== Jerkgram private Telegram API credentials =="
python3 ../../scripts/apply_jerkgram_build124_telegram_api_credentials1.py --variables build-input/configuration-repository/variables.bzl
python3 ../../scripts/verify_jerkgram_build124_telegram_api_credentials1.py --variables build-input/configuration-repository/variables.bzl

echo
echo "== Build113 unsigned ESign-ready signing setup =="
echo "Skip provisioning-profile decode, P12 import and temporary keychain"

echo
echo
echo "== patch BUILD compatibility globally =="
python3 ../../scripts/gb_patch_build.py

echo
echo "== cxxopts after global patch =="
grep -RIn "cxxopts[[:space:]]*=" Telegram submodules third-party Tests 2>/dev/null || true

echo
 echo "== patch Swift compatibility =="
python3 ../../scripts/gb_patch_swift.py

echo
echo "== global forbidden source grep =="
BAD="$(
find . -type f \( \
  -name "*.swift" -o \
  -name "*.m" -o \
  -name "*.mm" -o \
  -name "*.h" -o \
  -name "*.plist" -o \
  -name "*.entitlements" -o \
  -name "*.bzl" -o \
  -name "BUILD" -o \
  -name "BUILD.bazel" -o \
  -name "*.json" \
\) \
-not -path "*/.git/*" \
-not -path "*/bazel-*/*" \
-print0 | xargs -0 grep -InE 'app\.swiftgram\.ios|group\.app\.swiftgram\.ios|group\.4a348a9b186b700c\.10|group\.\\\(baseAppBundle' || true
)"

if [ -n "$BAD" ]; then
  echo "$BAD"
  echo "ERROR: forbidden Swiftgram/AppGroup source leftovers"
  exit 1
fi

echo "global forbidden source grep OK"

echo "== verify official Telegram signing config =="
echo "-- active config --"
grep -RInE 'telegram_team_id|telegram_bundle_id|telegram_app_group' \
  build-input/configuration-repository build-system/example-configuration || true

BAD_OFFICIAL="$(
grep -RInE 'telegram_team_id = "C67CF9S4VU"|telegram_bundle_id = "ph\.telegra\.Telegraph"|C67CF9S4VU\.ph\.telegra\.Telegraph' \
  Telegram build-input/configuration-repository build-system/example-configuration 2>/dev/null || true
)"
if [ -n "$BAD_OFFICIAL" ]; then
  echo "$BAD_OFFICIAL"
  echo "ERROR: official Telegram signing config leftovers"
  exit 1
fi
echo "official Telegram signing config OK"

echo "== verify official AppGroup entitlements =="
BAD_APPGROUP="$(
grep -RInE 'group\.app\.pumpkin6584\.lion7414|group\.\{telegram_bundle_id\}' \
  Telegram build-input/configuration-repository build-system/example-configuration 2>/dev/null || true
)"
if [ -n "$BAD_APPGROUP" ]; then
  echo "$BAD_APPGROUP"
  echo "ERROR: official AppGroup entitlement leftovers"
  exit 1
fi
echo "official AppGroup entitlements OK"

echo "== verify global Swift AppGroup patch =="
if grep -RInE 'guard let baseAppBundle|let baseAppBundle[A-Za-z0-9_]*[[:space:]]*=[[:space:]]*$' Swiftgram 2>/dev/null; then
  echo "Global Swift AppGroup verification failed"
  exit 1
fi


echo
echo "== patch unsupported entitlements =="
python3 ../../scripts/gb_patch_entitlements.py

echo "== skip Swiftgram-only compile probe for official Telegram =="

echo
echo "== verify helper scripts syntax =="
python3 -m py_compile ../../scripts/gb_patch_swift.py
python3 -m py_compile ../../scripts/gb_patch_entitlements.py
python3 -m py_compile ../../scripts/gb_verify_device_ipa.py

echo "[GhostBase] Fix v1.0E Push/RegisterDevice Swift helper syntax"
python3 ../../scripts/fix_ghostbase_push_probe_swift_v10e.py

echo "== real build probe =="
echo "GHOSTBASE_PROBE_ONLY=$GHOSTBASE_PROBE_ONLY"
echo "GHOSTBASE_BAZEL_TARGET=$GHOSTBASE_BAZEL_TARGET"

echo "== apply/verify GhostBase v1.0Y final overlay =="
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10y_bot_auth_core.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10y_bot_login_ui.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10y_bot_token_redaction.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10z_bot_login_runtime.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10y_multiselect_forward.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10y_repeated_voice.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10y_hidden_gifts_probe.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10z_hidden_gifts_core.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10z_hidden_gifts_deep_probe.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10y_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10z_hidden_gifts_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10z_bot_login_generated_source.py"

python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10za_hidden_gifts_send.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10za_hidden_gifts_self_anonymous.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10za_hidden_gifts_send_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10za_hidden_gifts_self_anonymous_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10za_bot_capability_core.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10za_bot_capability_ui.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10za_bot_capability_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10z_scheduled_voice_lifecycle.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10za_scheduled_voice_redirect.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10z_scheduled_voice_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10za_scheduled_voice_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zb_bot_difference_probe.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zb_bot_difference_ui.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zb_bot_difference_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zb_seasonal_gifts.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zb_seasonal_gifts_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zc_bot_inbox.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zc_bot_inbox_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10ze_botsafe1.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10ze_botsafe1_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zd_profileintel1_core.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zd_profileintel1_ui.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zd_profileintel1_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zf_botsafe2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zf_botsafe2_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zf_profileintel2_core.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zf_profileintel2_ui.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zf_profileintel2_generated_source.py"

# MARK: GhostBase v1.0ZG Build 85 package
echo "== apply/verify GhostBase v1.0ZG Build 85 =="
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zg_accountunlock_botlogout.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zg_private_invite_probe.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zg_profileintel3_personal_channel.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zg_gifthistory1_core.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zg_gifthistory1_ui.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zg_profileintel2_cleanup.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zg_accountunlock_botlogout_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zg_private_invite_probe_generated_source.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zg_profileintel3_personal_channel_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zg_gifthistory1_core_generated_source.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zg_gifthistory1_ui_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zg_profileintel2_cleanup_generated_source.py"
# END MARK: GhostBase v1.0ZG Build 85 package

# MARK: GhostBase v1.0ZH Build 86 full package
echo "== apply/verify GhostBase v1.0ZH Build 86 full package =="
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zh_botbootstrap1_botdedupe1.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zh_gifthistory2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zh_presencehistory1.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v10zh_profileui1.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zh_botbootstrap1_botdedupe1_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zh_gifthistory2_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zh_presencehistory1_generated_source.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v10zh_profileui1_generated_source.py"
# END MARK: GhostBase v1.0ZH Build 86 full package

# MARK: GhostBase v1.1a Build 87 full package
echo "== apply/verify GhostBase v1.1a Build 87 full package =="
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11a_bot_repair_backfill.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11a_profile_hub_channel.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11a_presence_global.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11a_transcription.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11a_version.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11a_bot_repair_backfill_generated_source.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11a_profile_hub_channel_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11a_presence_global_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11a_transcription_generated_source.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11a_version_generated_source.py"
# END MARK: GhostBase v1.1a Build 87 full package

# MARK: GhostBase v1.1B integrated release
echo "== apply/verify GhostBase v1.1B integrated release =="
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11b_presence_global2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11b_bot_backfill3.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11b_transcription2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11b_hidden_gifts1.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11b_profile_hub2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11b_presence_global2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11b_bot_backfill3.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11b_transcription2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11b_hidden_gifts1.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11b_profile_hub2.py"
# END MARK: GhostBase v1.1B integrated release


# MARK: GhostBase v1.1C Stage 1 candidate

echo "== apply/verify GhostBase v1.1C Stage 1 candidate =="
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11c_glass_core1.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11c_botstate4.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11c_settingsglass1.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11c_profileglass1.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11c_giftsglass1.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11c_version.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11c_glass_core1.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11c_botstate4.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11c_settingsglass1.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11c_profileglass1.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11c_giftsglass1.py"
echo "== v1.1C version verifier superseded by v1.1D =="
# END MARK: GhostBase v1.1C Stage 1 candidate

# MARK: GhostBase v1.1D reference rebuild candidate
echo "== apply/verify GhostBase v1.1D reference rebuild candidate =="
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11d_glass_core2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11d_botbackfill4_safe.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11d_settings_global2.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11d_profile_reference2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11d_gifts_glass2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11d_version.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11d_glass_core2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11d_botbackfill4_safe.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11d_settings_global2.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11d_profile_reference2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11d_gifts_glass2.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11d_version.py"
# END MARK: GhostBase v1.1D reference rebuild candidate

# MARK: GhostBase v1.1E audit rebuild candidate
echo "== apply/verify GhostBase v1.1E audit rebuild candidate =="
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11e_glass_runtime3.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11e_profile_native3.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11e_bot_shadow_history1.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11e_settings_gifts3.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11e_version.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11e_glass_runtime3.py"
# V11F-DISABLED-OLD-PROFILE-UI: python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11e_profile_native3.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11e_bot_shadow_history1.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11e_settings_gifts3.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11e_version.py"
# END MARK: GhostBase v1.1E audit rebuild candidate
# MARK: GhostBase v1.1F profile header blur
echo "== apply/verify GhostBase v1.1F profile header blur =="
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11f_profile_header_blur1.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11f_profile_header_blur1.py"
# END MARK: GhostBase v1.1F profile header blur
# MARK: GhostBase v1.1G unified recovery
echo "== apply/verify GhostBase v1.1G unified recovery =="
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/apply_ghostbase_v11g_unified_recovery1.py"

echo "== fix GhostBase v1.1G SettingsUI dedup =="
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/fix_ghostbase_v11g_settings_dedup.py"

echo "== fix GhostBase v1.1G PeerInfo compile =="
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/fix_ghostbase_v11g_peerinfo_compile.py"
python3 "$GHOSTBASE_BUILDER_ROOT/scripts/verify_ghostbase_v11g_unified_recovery1.py"

echo "== apply GhostBase v1.1H recovery =="
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11h_recovery1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11i_profile_final1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/fix_ghostbase_v11i_profile_history_compile.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11i_profile_final1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11k_profile_polish2.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11k_profile_polish2.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11l_profile_state_animation1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11l_profile_state_animation1.py"

python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11m_runtime_core1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11m_runtime_core1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11m_animation_coexist1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11m_animation_coexist1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11m_gifts_glass1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11m_gifts_glass1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11m_music_player_glass1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11m_music_player_glass1.py"

python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11n_profile_core_final1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11n_profile_core_final1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11o_visual_reset1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11o_visual_reset1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11p_full_correction1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11p_full_correction1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11q_full_runtime_correction1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11q_full_runtime_correction1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11r_runtime_polish1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11r_runtime_polish1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11s_runtime_recovery1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11s_runtime_recovery1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11t_build105_full1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11t_build105_full1.py"

# GhostBase v1.1U / Build106
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11u_build106_final1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11u_build106_final1_generated_source.py"

# GhostBase v1.1V / Build107
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_ghostbase_v11v_build107_quoteemoji_stickerfallback1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_ghostbase_v11v_build107_quoteemoji_stickerfallback1.py"

python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_jerkgram_v11w_build108_foundation1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_jerkgram_v11w_build108_foundation1.py"

python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_jerkgram_v11x_build109_foundation_hotfix1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_jerkgram_v11x_build109_foundation_hotfix1.py"

python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/apply_jerkgram_v11y_build110_icons_ui_recovery_polish1.py"
python3 "${GHOSTBASE_BUILDER_ROOT}/scripts/verify_jerkgram_v11y_build110_icons_ui_recovery_polish1.py"

echo "== Jerkgram v1.1Z Build111: native Glass Composer + UI fixes =="
python3 ../../scripts/apply_jerkgram_v11z_build111_glass_composer_ui_fix1.py
python3 ../../scripts/verify_jerkgram_v11z_build111_glass_composer_ui_fix1.py
python3 ../../scripts/apply_jerkgram_v12a_build112_composer_alternates_extensions1.py
python3 ../../scripts/verify_jerkgram_v12a_build112_composer_alternates_extensions1.py
echo "== Jerkgram v1.2B Build113 recovery =="
python3 ../../scripts/apply_jerkgram_v12b_build113_recovery1.py
python3 ../../scripts/verify_jerkgram_v12b_build113_recovery1.py
echo "== Jerkgram v1.2B Build113 profile recovery =="
python3 ../../scripts/apply_jerkgram_v12b_build113_profile_recovery1.py
python3 ../../scripts/verify_jerkgram_v12b_build113_profile_recovery1.py

echo
echo "== Jerkgram v1.2C Build114 source/runtime/UI =="
python3 ../../scripts/apply_jerkgram_v12c_build114_core1.py
python3 ../../scripts/verify_jerkgram_v12c_build114_core1.py

echo
echo "== Jerkgram v1.2D Build115 AppGroup selection =="
python3 ../../scripts/apply_jerkgram_v12d_build115_appgroup1.py
python3 ../../scripts/verify_jerkgram_v12d_build115_appgroup1.py

echo
echo "== Jerkgram v1.2D Build115 profile UI =="
python3 ../../scripts/apply_jerkgram_v12d_build115_profile_ui1.py
python3 ../../scripts/verify_jerkgram_v12d_build115_profile_ui1.py

echo
echo "== Jerkgram v1.2D Build115 localization foundation =="
python3 ../../scripts/apply_jerkgram_v12d_build115_localization1.py
python3 ../../scripts/verify_jerkgram_v12d_build115_localization1.py

echo
echo "== Jerkgram v1.2D Build115 research Settings canonicalization =="
python3 ../../scripts/apply_jerkgram_v12d_build115_research_settings1.py --phase canonical

echo
echo "== Jerkgram v1.2D Build115 Settings localization =="
python3 ../../scripts/apply_jerkgram_v12d_build115_settings_localization1.py
python3 ../../scripts/verify_jerkgram_v12d_build115_settings_localization1.py

echo
echo "== Jerkgram v1.2D Build115 research Settings localization =="
python3 ../../scripts/apply_jerkgram_v12d_build115_research_settings1.py --phase localized
python3 ../../scripts/verify_jerkgram_v12d_build115_research_settings1.py

echo
echo "== Jerkgram v1.2D Build115 recovery English baseline =="
python3 ../../scripts/apply_jerkgram_v12d_build115_recovery_english1.py
python3 ../../scripts/verify_jerkgram_v12d_build115_recovery_english1.py

echo
echo "== Jerkgram v1.2D Build115 numeric links =="
python3 ../../scripts/apply_jerkgram_v12d_build115_numeric_links1.py
python3 ../../scripts/verify_jerkgram_v12d_build115_numeric_links1.py

echo
echo "== Jerkgram v1.2E Build116 user-facing fixes =="
python3 ../../scripts/apply_jerkgram_v12e_build116_ui1.py
python3 ../../scripts/verify_jerkgram_v12e_build116_ui1.py

echo
echo "== Jerkgram v1.2E Build116 extension diagnostics =="
python3 ../../scripts/apply_jerkgram_v12e_build116_extensions1.py
python3 ../../scripts/verify_jerkgram_v12e_build116_extensions1.py

echo
echo "== Jerkgram v1.2E Build116 typed foundations =="
python3 ../../scripts/apply_jerkgram_v12e_build116_foundation1.py
python3 ../../scripts/verify_jerkgram_v12e_build116_foundation1.py

echo
echo "== Jerkgram v1.2F Build117 release-readiness update =="
python3 ../../scripts/apply_jerkgram_v12f_build117_profile_scope1.py
python3 ../../scripts/verify_jerkgram_v12f_build117_profile_scope1.py
python3 ../../scripts/apply_jerkgram_v12f_build117_about_channel1.py
python3 ../../scripts/verify_jerkgram_v12f_build117_about_channel1.py
python3 ../../scripts/apply_jerkgram_v12f_build117_profile_localization1.py
python3 ../../scripts/verify_jerkgram_v12f_build117_profile_localization1.py
python3 ../../scripts/apply_jerkgram_v12f_build117_extension_boundaries1.py
python3 ../../scripts/verify_jerkgram_v12f_build117_extension_boundaries1.py
python3 ../../scripts/verify_jerkgram_v12f_build117_release_readiness1.py

echo
echo "== Jerkgram v1.2G Build118 =="
python3 ../../scripts/apply_jerkgram_v12g_build118_core1.py
python3 ../../scripts/verify_jerkgram_v12g_build118_core1.py
python3 ../../scripts/apply_jerkgram_v12g_build118_storage1.py
python3 ../../scripts/verify_jerkgram_v12g_build118_storage1.py
python3 ../../scripts/apply_jerkgram_v12g_build118_time_machine1.py
python3 ../../scripts/verify_jerkgram_v12g_build118_time_machine1.py
python3 ../../scripts/apply_jerkgram_v12g_build118_archive1.py
python3 ../../scripts/verify_jerkgram_v12g_build118_archive1.py
python3 ../../scripts/apply_jerkgram_v12g_build118_about_cards1.py
python3 ../../scripts/verify_jerkgram_v12g_build118_about_cards1.py
python3 ../../scripts/apply_jerkgram_v12g_build118_profile_report_polish1.py
python3 ../../scripts/verify_jerkgram_v12g_build118_profile_report_polish1.py
python3 ../../scripts/apply_jerkgram_v12g_build118_integration1.py
python3 ../../scripts/apply_jerkgram_v12g_build118_data_ui1.py
python3 ../../scripts/verify_jerkgram_v12g_build118_data_ui1.py
python3 ../../scripts/apply_jerkgram_v12g_build118_time_machine_ui1.py
python3 ../../scripts/verify_jerkgram_v12g_build118_time_machine_ui1.py
python3 ../../scripts/apply_jerkgram_v12g_build118_glass1.py
python3 ../../scripts/verify_jerkgram_v12g_build118_glass1.py
python3 ../../scripts/apply_jerkgram_v12g_build118_since_last_open1.py
python3 ../../scripts/verify_jerkgram_v12g_build118_since_last_open1.py
python3 ../../scripts/verify_jerkgram_v12g_build118_release_readiness1.py

echo
echo "== Jerkgram v1.2H Build119 hybrid UI =="
python3 ../../scripts/apply_jerkgram_v12h_build119_hybrid_ui2.py
python3 ../../scripts/verify_jerkgram_v12h_build119_hybrid_ui1.py

echo
echo "== Jerkgram v1.2I Build120 profile lifecycle + sticker alpha =="
python3 ../../scripts/apply_jerkgram_v12i_build120_profile_blur_lifecycle1.py
python3 ../../scripts/verify_jerkgram_v12i_build120_profile_blur_lifecycle1.py
python3 ../../scripts/apply_jerkgram_v12i_build120_sticker_alpha1.py
python3 ../../scripts/verify_jerkgram_v12i_build120_sticker_alpha1.py

echo
echo "== Jerkgram v1.2J Build121 native sticker recovery =="
python3 ../../scripts/apply_jerkgram_v12j_build121_sticker_recovery1.py
python3 ../../scripts/verify_jerkgram_v12j_build121_sticker_recovery1.py

echo
echo "== Jerkgram v1.2K Build122 reply/sticker runtime contracts =="
python3 ../../scripts/apply_jerkgram_v12k_build122_reply_sticker_contract1.py
python3 ../../scripts/verify_jerkgram_v12k_build122_reply_sticker_contract1.py
python3 ../../scripts/apply_jerkgram_v12k_build122_edit_caption_history1.py
python3 ../../scripts/verify_jerkgram_v12k_build122_edit_caption_history1.py
python3 ../../scripts/apply_jerkgram_v12k_build122_settings_release1.py
python3 ../../scripts/verify_jerkgram_v12k_build122_settings_release1.py

echo
echo "== Jerkgram v1.2L Build123 release recovery =="
python3 ../../scripts/apply_jerkgram_v12l_build123_state_runtime1.py
python3 ../../scripts/apply_jerkgram_v12l_build123_message_fidelity1.py
python3 ../../scripts/apply_jerkgram_v12l_build123_profile_ui1.py
python3 ../../scripts/apply_jerkgram_v12l_build123_settings_ui1.py
python3 ../../scripts/verify_jerkgram_v12l_build123_release_recovery1.py

# JERKGRAM_V12M_BUILD124_SOURCE_HOOK
echo
echo "== Jerkgram v1.2M Build124 runtime fixes =="
python3 ../../scripts/apply_jerkgram_v12m_build124_profile_edit_glass1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_profile_more1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_links_glass1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_single_forward1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_sensitive_settings1.py
python3 ../../scripts/debug_jerkgram_v12m_build124_settings_signal_shape1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_archive_import_runtime1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_archive_export_runtime1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_protected_forward1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_deleted_entities1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_edit_history1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_auth_keyboard1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_lifecycle_freeze1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_onetime_persistence1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_onetime_viewed1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_settings_redesign1.py

python3 ../../scripts/verify_jerkgram_v12m_build124_profile_edit_glass1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_profile_more1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_links_glass1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_single_forward1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_sensitive_settings1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_archive_import_runtime1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_archive_export_runtime1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_protected_forward1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_deleted_entities1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_edit_history1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_auth_keyboard1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_lifecycle_freeze1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_onetime_persistence1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_onetime_viewed1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_settings_redesign1.py

# JERKGRAM_V12N_BUILD125_SOURCE_HOOK

echo
echo "== Jerkgram v1.2N Build125 release owners =="
python3 ../../scripts/apply_jerkgram_v12n_build125_profile_edit1.py
python3 ../../scripts/apply_jerkgram_v12n_build125_single_forward1.py
python3 ../../scripts/apply_jerkgram_v12n_build125_circle_viewed1.py
python3 ../../scripts/apply_jerkgram_v12n_build125_links_bounds1.py
python3 ../../scripts/apply_jerkgram_v12n_build125_protected_cache1.py
python3 ../../scripts/apply_jerkgram_v12n_build125_auth_ghost_localization1.py
python3 ../../scripts/apply_jerkgram_v12m_build124_bot_localization1.py
python3 ../../scripts/verify_jerkgram_v12n_build125_profile_edit1.py
python3 ../../scripts/verify_jerkgram_v12n_build125_single_forward1.py
python3 ../../scripts/verify_jerkgram_v12n_build125_circle_viewed1.py
python3 ../../scripts/verify_jerkgram_v12n_build125_links_bounds1.py
python3 ../../scripts/verify_jerkgram_v12n_build125_protected_cache1.py
python3 ../../scripts/verify_jerkgram_v12n_build125_auth_ghost_localization1.py
python3 ../../scripts/verify_jerkgram_v12m_build124_bot_localization1.py

echo
echo "== Jerkgram v1.2O Build126 owner corrections =="
python3 ../../scripts/apply_jerkgram_v12o_build126_bio_corner_mask1.py
python3 ../../scripts/apply_jerkgram_v12o_build126_voice_viewed_state1.py
python3 ../../scripts/apply_jerkgram_v12o_build126_circle_viewed_state1.py
python3 ../../scripts/apply_jerkgram_v12o_build126_forward_menu_owner1.py

echo
echo "== Jerkgram v1.2P Build127 native one-time statuses =="
python3 ../../scripts/apply_jerkgram_v12p_build127_onetime_native_status1.py

echo
echo "== Jerkgram v1.2Q Build128 profile bio corner owner =="
python3 ../../scripts/apply_jerkgram_v12q_build128_bio_corner_owner1.py

echo
echo "== Jerkgram v1.2R Build129 protected chat forwarding =="
python3 ../../scripts/apply_jerkgram_v12r_build129_protected_chat_forward1.py

# JERKGRAM_V12S_BUILD130_SIRI_FAILCLOSED_HOOK
echo
echo "== Jerkgram v1.2S Build130 Siri runtime fail-closed =="
python3 ../../scripts/apply_jerkgram_v12s_build130_siri_failclosed1.py
python3 ../../scripts/verify_jerkgram_v12s_build130_siri_failclosed1.py

# JERKGRAM_V12W_BUILD133_RUNTIME_REPAIR_HOOK
echo
echo "== Jerkgram Build137 performance hardening =="
python3 ../../scripts/apply_jerkgram_v12t_build133_blocked_reactions1.py
python3 ../../scripts/verify_jerkgram_v12t_build133_blocked_reactions1.py
python3 ../../scripts/apply_jerkgram_v12u_build133_blocked_activity2.py
python3 ../../scripts/verify_jerkgram_v12u_build133_blocked_activity1.py
python3 ../../scripts/apply_jerkgram_v12v_build133_settings2.py
python3 ../../scripts/verify_jerkgram_v12v_build133_settings1.py
python3 ../../scripts/apply_jerkgram_v12x_build133_release_ui1.py
python3 ../../scripts/verify_jerkgram_v12x_build133_release_ui1.py
python3 ../../scripts/apply_jerkgram_v12y_build133_telemetry2.py
python3 ../../scripts/verify_jerkgram_v12y_build133_telemetry2.py
python3 ../../scripts/apply_jerkgram_v12z_build134_context_localization1.py
python3 ../../scripts/verify_jerkgram_v12z_build134_context_localization1.py
python3 ../../scripts/apply_jerkgram_v12za_build134_gift_localization1.py
python3 ../../scripts/verify_jerkgram_v12za_build134_gift_localization1.py
python3 ../../scripts/apply_jerkgram_v12zb_build135_visibility_runtime1.py
python3 ../../scripts/verify_jerkgram_v12zb_build135_visibility_runtime1.py
python3 ../../scripts/apply_jerkgram_v12zc_build136_visible_order_cache1.py
python3 ../../scripts/verify_jerkgram_v12zc_build136_visible_order_cache1.py
python3 ../../scripts/apply_jerkgram_v12zd_build137_performance1.py
python3 ../../scripts/verify_jerkgram_v12zd_build137_performance1.py
python3 ../../scripts/apply_jerkgram_build137_performance2.py
python3 ../../scripts/verify_jerkgram_build137_performance2.py
python3 ../../scripts/apply_jerkgram_v12w_build133_music_overlay1.py
python3 ../../scripts/verify_jerkgram_v12w_build133_music_overlay1.py
python3 ../../scripts/verify_jerkgram_v12w_build133_runtime_repair1.py
# END MARK: GhostBase v1.1G unified recovery
"$BAZEL_BIN" build ${BAZEL_EXTRA_ARGS:-} \
  --enable_workspace \
  -c opt \
  --apple_platform_type=ios \
  --ios_multi_cpus=arm64 \
  --check_direct_dependencies=off \
  --//Telegram:disableExtensions=false \
  --//Telegram:disableProvisioningProfiles=true \
  --features=disable_legacy_signing \
  "$GHOSTBASE_BAZEL_TARGET"

echo
echo

if [ "${GHOSTBASE_PROBE_ONLY:-0}" = "1" ]; then
  echo "== probe-only build OK =="
  exit 0
fi

echo
echo "== save IPA before verifier =="
mkdir -p ghostbase-final
if [ -f bazel-bin/Telegram/Telegram.ipa ]; then
  cp -f bazel-bin/Telegram/Telegram.ipa ghostbase-final/GhostBase.ipa
  echo "IPA=bazel-bin/Telegram/Telegram.ipa" > ghostbase-final/info.txt
  echo "Final=ghostbase-final/GhostBase.ipa" >> ghostbase-final/info.txt
  TELEGRAM_VERSION="$(python3 -c 'import json; print(json.load(open("versions.json"))["app"])')"
  TELEGRAM_COMMIT="$(git rev-parse HEAD)"
  TELEGRAM_TAG="$(git tag --points-at HEAD | head -n 1)"
  echo "TelegramVersion=$TELEGRAM_VERSION" >> ghostbase-final/info.txt
  echo "TelegramCommit=$TELEGRAM_COMMIT" >> ghostbase-final/info.txt
  echo "TelegramTag=$TELEGRAM_TAG" >> ghostbase-final/info.txt
  cat ghostbase-final/info.txt
  ls -lh ghostbase-final/GhostBase.ipa
else
  echo "ERROR: bazel-bin/Telegram/Telegram.ipa missing"
  exit 1
fi

echo "== patch final IPA AppGroup .10 before verifier =="
python3 ../../scripts/patch_final_ipa_appgroup_build113.py ghostbase-final/GhostBase.ipa

echo "== strict GhostBase final IPA marker gate =="
TMP_GB_CHECK="$(mktemp -d)"
unzip -q "ghostbase-final/GhostBase.ipa" -d "$TMP_GB_CHECK"

echo "-- detected GhostBase markers --"




LC_ALL=C grep -RaoE "Version: v1\.1G-unified-recovery|SH1 Share Scheduled Send|GhostBase\.SH1\.ShareScheduledIntercept|OT1 Timer Media Local Keep|GhostBase\.OT1\.OutgoingKeepBlocked" "$TMP_GB_CHECK/Payload" 2>/dev/null | sort -u | sed -n '1,160p' || true

echo "-- verify Version: v1.1G-unified-recovery --"
if ! LC_ALL=C grep -Rao "Version: v1.1G-unified-recovery" "$TMP_GB_CHECK/Payload" >/dev/null 2>&1; then
  echo "::error::Final IPA does not contain Version: v1.1G-unified-recovery"
  exit 1
fi


echo "-- verify SH1 marker --"
if ! LC_ALL=C grep -Rao "SH1 Share Scheduled Send" "$TMP_GB_CHECK/Payload" >/dev/null 2>&1; then
  echo "::error::Final IPA does not contain SH1 marker"
  exit 1
fi

echo "-- verify OT1 marker --"
if ! LC_ALL=C grep -Rao "OT1 Timer Media Local Keep" "$TMP_GB_CHECK/Payload" >/dev/null 2>&1; then
  echo "::error::Final IPA does not contain OT1 marker"
  exit 1
fi


echo "== strict GhostBase final IPA marker gate OK =="


echo
echo "== finalize Build113 ESign-ready IPA =="
python3 ../../scripts/jerkgram_finalize_build113_esign_ready.py \
  ghostbase-final/GhostBase.ipa

echo "== verify Build113 final ESign-ready IPA =="
python3 ../../scripts/verify_jerkgram_v12b_build113_final_ipa.py \
  ghostbase-final/GhostBase.ipa

echo
echo "== finalize Build114 public/resign-ready IPA =="
python3 ../../scripts/jerkgram_finalize_build114_resign_ready.py   ghostbase-final/GhostBase.ipa

echo "== verify Build114 final public/resign-ready IPA =="
python3 ../../scripts/verify_jerkgram_v12c_build114_final_ipa.py   ghostbase-final/GhostBase.ipa

echo
echo "== Jerkgram v1.2H Build119 final identity =="
python3 ../../scripts/jerkgram_finalize_build119_identity.py ghostbase-final/GhostBase.ipa
python3 ../../scripts/verify_jerkgram_v12h_build119_final_ipa.py ghostbase-final/GhostBase.ipa

echo
echo "== Jerkgram v1.2I Build120 final identity =="
python3 ../../scripts/jerkgram_finalize_build120_identity.py ghostbase-final/GhostBase.ipa
python3 ../../scripts/verify_jerkgram_v12i_build120_final_ipa.py ghostbase-final/GhostBase.ipa

echo
echo "== Jerkgram v1.2J Build121 final identity =="
python3 ../../scripts/jerkgram_finalize_build121_identity.py ghostbase-final/GhostBase.ipa
python3 ../../scripts/verify_jerkgram_v12j_build121_final_ipa.py ghostbase-final/GhostBase.ipa

echo
echo "== Jerkgram v1.2K Build122 final identity =="
python3 ../../scripts/jerkgram_finalize_build122_identity.py ghostbase-final/GhostBase.ipa
python3 ../../scripts/verify_jerkgram_v12k_build122_final_ipa.py ghostbase-final/GhostBase.ipa

echo
echo "== Jerkgram v1.2L Build123 final identity =="
python3 ../../scripts/jerkgram_finalize_build123_identity.py ghostbase-final/GhostBase.ipa
python3 ../../scripts/verify_jerkgram_v12l_build123_final_ipa.py ghostbase-final/GhostBase.ipa

# JERKGRAM_V12M_BUILD124_FINAL_IDENTITY_HOOK
echo
echo "== Jerkgram v1.2M Build124 final identity =="
python3 ../../scripts/jerkgram_finalize_build124_identity.py ghostbase-final/GhostBase.ipa
python3 ../../scripts/verify_jerkgram_v12m_build124_final_ipa.py ghostbase-final/GhostBase.ipa

# JERKGRAM_V12N_BUILD125_FINAL_IDENTITY_HOOK
echo
echo "== Jerkgram v1.2N Build125 final identity =="
python3 ../../scripts/jerkgram_finalize_build125_identity.py ghostbase-final/GhostBase.ipa
python3 ../../scripts/verify_jerkgram_v12n_build125_final_ipa.py ghostbase-final/GhostBase.ipa

echo
echo "== Jerkgram Build128 final identity and audited compatibility packages =="
python3 ../../scripts/jerkgram_finalize_build128_identity.py ghostbase-final/GhostBase.ipa
python3 ../../scripts/verify_jerkgram_v12s_build128_final_ipa.py ghostbase-final/GhostBase.ipa

# JERKGRAM_V12S_BUILD130_FINAL_IDENTITY_HOOK
echo
echo "== Jerkgram Build130 final identity =="
python3 ../../scripts/jerkgram_finalize_build130_identity.py ghostbase-final/GhostBase.ipa
python3 ../../scripts/verify_jerkgram_v12s_build130_final_ipa.py ghostbase-final/GhostBase.ipa

# JERKGRAM_V12W_BUILD133_FINAL_IDENTITY_HOOK
echo
echo "== Jerkgram Build137 final identity =="
python3 ../../scripts/jerkgram_finalize_build133_identity.py ghostbase-final/GhostBase.ipa
python3 ../../scripts/verify_jerkgram_v12w_build133_final_ipa.py ghostbase-final/GhostBase.ipa
