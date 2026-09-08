#!/usr/bin/env python3

from pathlib import Path
import plistlib
import sys
import tempfile
import zipfile

EXPECTED_BUNDLE = "com.jerkgram.ios"
EXPECTED_TELEGRAM_VERSION = "12.9.2"
EXPECTED_BUILD = "136"
EXPECTED_DISPLAY = "Jerkgram"
EXTENSION_SUFFIXES = {
    "BroadcastUploadExtension.appex": "BroadcastUpload",
    "IntentsExtension.appex": "SiriIntents",
    "NotificationContentExtension.appex": "NotificationContent",
    "NotificationServiceExtensionv1.appex": "NotificationService",
    "ShareExtension.appex": "Share",
    "WidgetExtension.appex": "Widget",
}


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
        require(str(info.get("CFBundleVersion")) == EXPECTED_BUILD, "CFBundleVersion is not 136")
        require(info.get("CFBundleDisplayName") == EXPECTED_DISPLAY, "CFBundleDisplayName is not Jerkgram")
        require(info.get("CFBundleName") == EXPECTED_DISPLAY, "CFBundleName is not Jerkgram")
        require(not (app / "embedded.mobileprovision").exists(), "main embedded.mobileprovision present")

        plugins_root = app / "PlugIns"
        plugins = {path.name: path for path in plugins_root.glob("*.appex") if path.is_dir()}
        require(set(plugins) == set(EXTENSION_SUFFIXES), "extension topology mismatch")
        for name, suffix in EXTENSION_SUFFIXES.items():
            extension = plugins[name]
            with (extension / "Info.plist").open("rb") as file:
                extension_info = plistlib.load(file)
            expected = EXPECTED_BUNDLE + "." + suffix
            require(extension_info.get("CFBundleIdentifier") == expected, f"{name} CFBundleIdentifier is not {expected}")
            require(str(extension_info.get("CFBundleVersion")) == EXPECTED_BUILD, f"{name} CFBundleVersion is not 136")
            require(not (extension / "embedded.mobileprovision").exists(), f"{name} embedded.mobileprovision present")


def main() -> None:
    ipa = Path(sys.argv[1] if len(sys.argv) > 1 else "work/swiftgram-src/ghostbase-final/GhostBase.ipa").resolve()
    # The canonical workflow runs the complete Build130 verifier immediately
    # before the Build136 namespace rebase. Re-running that old-namespace gate
    # here would reject the requested com.jerkgram.ios identity.
    verify_build133_identity(ipa)
    print("[Build136 final IPA verify] GREEN")
    print("[Build136 final IPA verify] com.jerkgram.ios / Telegram 12.9.2 / Build 136")


if __name__ == "__main__":
    main()
