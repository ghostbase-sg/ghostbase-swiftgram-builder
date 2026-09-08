#!/usr/bin/env python3

from pathlib import Path
import os
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
PROBE = Path(os.environ.get("JERKGRAM_PROBE_PATH", str(SCRIPT_DIR / "bazel_build_probe_official.sh"))).resolve()
BASE_INSTALLER = SCRIPT_DIR / "install_jerkgram_v12s_build130_probe_hook.py"

SOURCE_MARKER = "# JERKGRAM_V12W_BUILD133_RUNTIME_REPAIR_HOOK"
FINAL_MARKER = "# JERKGRAM_V12W_BUILD133_FINAL_IDENTITY_HOOK"
BUILD130_SOURCE_ANCHOR = "python3 ../../scripts/verify_jerkgram_v12s_build130_siri_failclosed1.py"
BUILD130_FINAL_ANCHOR = "python3 ../../scripts/verify_jerkgram_v12s_build130_final_ipa.py ghostbase-final/GhostBase.ipa"
BAZEL_ANCHOR = '"$BAZEL_BIN" build ${BAZEL_EXTRA_ARGS:-}'

SOURCE_ORDERED = (
    "apply_jerkgram_v12t_build133_blocked_reactions1.py",
    "verify_jerkgram_v12t_build133_blocked_reactions1.py",
    "apply_jerkgram_v12u_build133_blocked_activity2.py",
    "verify_jerkgram_v12u_build133_blocked_activity1.py",
    "apply_jerkgram_v12v_build133_settings2.py",
    "verify_jerkgram_v12v_build133_settings1.py",
    "apply_jerkgram_v12x_build133_release_ui1.py",
    "verify_jerkgram_v12x_build133_release_ui1.py",
    "apply_jerkgram_v12y_build133_telemetry2.py",
    "verify_jerkgram_v12y_build133_telemetry2.py",
    "apply_jerkgram_v12z_build134_context_localization1.py",
    "verify_jerkgram_v12z_build134_context_localization1.py",
    "apply_jerkgram_v12za_build134_gift_localization1.py",
    "verify_jerkgram_v12za_build134_gift_localization1.py",
    "apply_jerkgram_v12zb_build135_visibility_runtime1.py",
    "verify_jerkgram_v12zb_build135_visibility_runtime1.py",
    "apply_jerkgram_v12zc_build136_visible_order_cache1.py",
    "verify_jerkgram_v12zc_build136_visible_order_cache1.py",
    "apply_jerkgram_v12w_build133_music_overlay1.py",
    "verify_jerkgram_v12w_build133_music_overlay1.py",
    "verify_jerkgram_v12w_build133_runtime_repair1.py",
)
FINAL_ORDERED = (
    "jerkgram_finalize_build133_identity.py",
    "verify_jerkgram_v12w_build133_final_ipa.py",
)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 probe hook] " + message)


def line(name: str, argument: str | None = None) -> str:
    value = "python3 ../../scripts/" + name
    return value if argument is None else value + " " + argument


def patch_probe(text: str) -> str:
    require(text.count(BUILD130_SOURCE_ANCHOR) == 1, "Build130 source anchor count")
    require(text.count(BUILD130_FINAL_ANCHOR) == 1, "Build130 final anchor count")
    require(text.count(BAZEL_ANCHOR) == 1, "Bazel anchor count")

    source_payload = (
        SOURCE_MARKER
        + '\necho\necho "== Jerkgram Build136 runtime repair =="\n'
        + "\n".join(line(name) for name in SOURCE_ORDERED)
    )
    if SOURCE_MARKER not in text:
        require(all(text.count(name) == 0 for name in SOURCE_ORDERED), "partial preexisting Build133 source block")
        source_block = (
            BUILD130_SOURCE_ANCHOR
            + "\n\n" + source_payload
        )
        text = text.replace(BUILD130_SOURCE_ANCHOR, source_block, 1)
    else:
        source_start = text.index(SOURCE_MARKER)
        end_mark = text.find("# END MARK:", source_start)
        bazel_start = text.index(BAZEL_ANCHOR)
        source_end = end_mark if 0 <= end_mark < bazel_start else bazel_start
        text = text[:source_start] + source_payload + "\n" + text[source_end:]

    require(text.count(SOURCE_MARKER) == 1, "Build133 source marker count")
    source_positions = [text.index(name) for name in SOURCE_ORDERED]
    require(source_positions == sorted(source_positions), "Build133 source apply/verifier order")
    require(all(text.count(name) == 1 for name in SOURCE_ORDERED), "Build133 source hook count")
    require(text.index(BUILD130_SOURCE_ANCHOR) < source_positions[0], "Build133 must follow Build130")
    require(source_positions[-1] < text.index(BAZEL_ANCHOR), "Build133 final source verifier must precede Bazel")

    if FINAL_MARKER not in text:
        require(all(text.count(name) == 0 for name in FINAL_ORDERED), "partial preexisting Build133 final block")
        final_block = (
            BUILD130_FINAL_ANCHOR
            + "\n\n" + FINAL_MARKER
            + '\necho\necho "== Jerkgram Build136 final identity =="\n'
            + "\n".join(line(name, "ghostbase-final/GhostBase.ipa") for name in FINAL_ORDERED)
        )
        text = text.replace(BUILD130_FINAL_ANCHOR, final_block, 1)

    require(text.count(FINAL_MARKER) == 1, "Build133 final marker count")
    final_positions = [text.index(name) for name in FINAL_ORDERED]
    require(final_positions == sorted(final_positions), "Build133 final identity order")
    require(all(text.count(name) == 1 for name in FINAL_ORDERED), "Build133 final hook count")
    require(text.index(BUILD130_FINAL_ANCHOR) < final_positions[0], "Build133 final identity must follow Build130 verification")
    text = text.replace("== Jerkgram Build134 final identity ==", "== Jerkgram Build136 final identity ==")
    text = text.replace("== Jerkgram Build135 final identity ==", "== Jerkgram Build136 final identity ==")
    return text


def main() -> None:
    require(BASE_INSTALLER.is_file(), "base installer missing: " + str(BASE_INSTALLER))
    subprocess.check_call([sys.executable, str(BASE_INSTALLER)])
    require(PROBE.is_file(), "probe missing: " + str(PROBE))
    PROBE.write_text(patch_probe(PROBE.read_text(encoding="utf-8")), encoding="utf-8")
    print("[Build136 probe hook] GREEN")
    print("[Build136 probe hook] Telemetry 2.1 -> reactions/activity/navigation -> Settings2 -> localization -> visible preview/unread/account runtime -> visible ordering/cache -> music -> final source gate -> Bazel")


if __name__ == "__main__":
    main()
