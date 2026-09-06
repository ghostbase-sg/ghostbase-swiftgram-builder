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
    "apply_jerkgram_v12u_build133_blocked_activity1.py",
    "verify_jerkgram_v12u_build133_blocked_activity1.py",
    "apply_jerkgram_v12v_build133_settings1.py",
    "verify_jerkgram_v12v_build133_settings1.py",
    "apply_jerkgram_v12w_build133_music_overlay1.py",
    "verify_jerkgram_v12w_build133_music_overlay1.py",
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

    if SOURCE_MARKER not in text:
        require(all(text.count(name) == 0 for name in SOURCE_ORDERED), "partial preexisting Build133 source block")
        source_block = (
            BUILD130_SOURCE_ANCHOR
            + "\n\n" + SOURCE_MARKER
            + '\necho\necho "== Jerkgram v1.2T-W Build133 runtime repair =="\n'
            + "\n".join(line(name) for name in SOURCE_ORDERED)
        )
        text = text.replace(BUILD130_SOURCE_ANCHOR, source_block, 1)

    require(text.count(SOURCE_MARKER) == 1, "Build133 source marker count")
    source_positions = [text.index(name) for name in SOURCE_ORDERED]
    require(source_positions == sorted(source_positions), "Build133 source apply/verifier order")
    require(all(text.count(name) == 1 for name in SOURCE_ORDERED), "Build133 source hook count")
    require(text.index(BUILD130_SOURCE_ANCHOR) < source_positions[0], "Build133 must follow Build130")
    require(source_positions[-1] < text.index(BAZEL_ANCHOR), "Build133 source verifier must precede Bazel")

    if FINAL_MARKER not in text:
        require(all(text.count(name) == 0 for name in FINAL_ORDERED), "partial preexisting Build133 final block")
        final_block = (
            BUILD130_FINAL_ANCHOR
            + "\n\n" + FINAL_MARKER
            + '\necho\necho "== Jerkgram Build133 final identity =="\n'
            + "\n".join(line(name, "ghostbase-final/GhostBase.ipa") for name in FINAL_ORDERED)
        )
        text = text.replace(BUILD130_FINAL_ANCHOR, final_block, 1)

    require(text.count(FINAL_MARKER) == 1, "Build133 final marker count")
    final_positions = [text.index(name) for name in FINAL_ORDERED]
    require(final_positions == sorted(final_positions), "Build133 final identity order")
    require(all(text.count(name) == 1 for name in FINAL_ORDERED), "Build133 final hook count")
    require(text.index(BUILD130_FINAL_ANCHOR) < final_positions[0], "Build133 final identity must follow Build130 verification")
    return text


def main() -> None:
    require(BASE_INSTALLER.is_file(), "base installer missing: " + str(BASE_INSTALLER))
    subprocess.check_call([sys.executable, str(BASE_INSTALLER)])
    require(PROBE.is_file(), "probe missing: " + str(PROBE))
    PROBE.write_text(patch_probe(PROBE.read_text(encoding="utf-8")), encoding="utf-8")
    print("[Build133 probe hook] GREEN")
    print("[Build133 probe hook] Build130 -> v12t reactions -> v12u activity/navigation -> v12v Settings -> v12w music -> Bazel")


if __name__ == "__main__":
    main()
