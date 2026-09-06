#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
ORDERED = (
    "verify_jerkgram_v12t_build133_blocked_reactions1.py",
    "verify_jerkgram_v12u_build133_blocked_activity1.py",
    "verify_jerkgram_v12v_build133_settings1.py",
    "verify_jerkgram_v12w_build133_music_overlay1.py",
)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 final source verifier] " + message)


def main() -> None:
    for name in ORDERED:
        path = SCRIPT_DIR / name
        require(path.is_file(), "missing verifier: " + name)
        subprocess.run([sys.executable, str(path)], check=True)
    print("[Build133 final source verifier] PREFLIGHT GREEN")


if __name__ == "__main__":
    main()
