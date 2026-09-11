#!/usr/bin/env python3
from pathlib import Path
import os
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import apply_jerkgram_build140_identity as patch

ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
STRINGS = ROOT / "submodules/TelegramPresentationData/Sources/JerkgramStrings.swift"


def main() -> None:
    patch.require(STRINGS.is_file(), "JerkgramStrings missing: " + str(STRINGS))
    text = STRINGS.read_text(encoding="utf-8")
    patch.verify_transformed(text)
    print("[Build140 identity verify] PREFLIGHT GREEN")
    print("[Build140 identity verify] 1.0.2 / Build 140 / Telegram Base 12.9.2")


if __name__ == "__main__":
    main()
