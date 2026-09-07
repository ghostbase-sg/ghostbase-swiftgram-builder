#!/usr/bin/env python3

from pathlib import Path
import plistlib
import sys
import tempfile
import zipfile

import verify_jerkgram_v12s_build130_final_ipa as base


EXPECTED_BUNDLE = "com.jerkgram.ios"
EXPECTED_TELEGRAM_VERSION = "12.9.2"
EXPECTED_BUILD = "134"
EXPECTED_DISPLAY = "Jerkgram"

base.base.base.EXPECTED_BUILD = EXPECTED_BUILD
base.base.base.EXPECTED_BUNDLE = EXPECTED_BUNDLE


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 final IPA verify] " + message)


def verify_build133_identity(ipa: Path) -> None:
    require(ipa.is_file(), "IPA missing: " + str(ipa))
    with tempfile.TemporaryDirectory(prefix="jerkgram-build133-identity-") as directory:
        root = Path(directory)
        with zipfile.ZipFile(ipa, "r") as archive:
            archive.extractall(root)
        apps = list((root / "Payload").glob("*.app"))
        require(len(apps) == 1, "expected exactly one main app")
        app = apps[0]
        with (app / "Info.plist").open("rb") as file:
            info = plistlib.load(file)

        require(info.get("CFBundleIdentifier") == EXPECTED_BUNDLE, "CFBundleIdentifier is not com.jerkgram.ios")
        require(info.get("CFBundleShortVersionString") == EXPECTED_TELEGRAM_VERSION, "CFBundleShortVersionString changed from Telegram 12.9.2")
        require(str(info.get("CFBundleVersion")) == EXPECTED_BUILD, "CFBundleVersion is not 134")
        require(info.get("CFBundleDisplayName") == EXPECTED_DISPLAY, "CFBundleDisplayName is not Jerkgram")
        require(info.get("CFBundleName") == EXPECTED_DISPLAY, "CFBundleName is not Jerkgram")


def main() -> None:
    ipa = Path(sys.argv[1] if len(sys.argv) > 1 else "work/swiftgram-src/ghostbase-final/GhostBase.ipa").resolve()
    # Keep every Build130 packaging/keychain/extension gate, then add the exact
    # Build133 public identity contract observed in the last-good Build130 IPA.
    base.main()
    verify_build133_identity(ipa)
    print("[Build134 final IPA verify] GREEN")
    print("[Build134 final IPA verify] com.jerkgram.ios / Telegram 12.9.2 / Build 134")


if __name__ == "__main__":
    main()
