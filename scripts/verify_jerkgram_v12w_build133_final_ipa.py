#!/usr/bin/env python3

from pathlib import Path
import plistlib
import sys
import tempfile
import zipfile

EXPECTED_BUNDLE = "com.jerkgram.ios"
EXPECTED_TELEGRAM_VERSION = "12.9.2"
EXPECTED_BUILD = "140"
EXPECTED_DISPLAY = "Jerkgram"
EXPECTED_URL_SCHEMES = {"jerkgram", "telegram", "tg"}
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
        raise RuntimeError("[Build140 final IPA verify] " + message)


def app_url_schemes(info: dict) -> set[str]:
    result: set[str] = set()
    for entry in info.get("CFBundleURLTypes", []) or []:
        if not isinstance(entry, dict):
            continue
        for value in entry.get("CFBundleURLSchemes", []) or []:
            if isinstance(value, str):
                result.add(value)
    return result


def verify_build140_identity(ipa: Path) -> None:
    require(ipa.is_file(), "IPA missing: " + str(ipa))
    with tempfile.TemporaryDirectory(prefix="jerkgram-build140-identity-") as directory:
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
        require(str(info.get("CFBundleVersion")) == EXPECTED_BUILD, "CFBundleVersion is not 140")
        require(info.get("CFBundleDisplayName") == EXPECTED_DISPLAY, "CFBundleDisplayName is not Jerkgram")
        require(info.get("CFBundleName") == EXPECTED_DISPLAY, "CFBundleName is not Jerkgram")
        schemes = app_url_schemes(info)
        missing_schemes = sorted(EXPECTED_URL_SCHEMES - schemes)
        require(not missing_schemes, "main app URL schemes missing: " + ", ".join(missing_schemes))
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
            require(str(extension_info.get("CFBundleVersion")) == EXPECTED_BUILD, f"{name} CFBundleVersion is not 140")
            require(not (extension / "embedded.mobileprovision").exists(), f"{name} embedded.mobileprovision present")


def main() -> None:
    ipa = Path(sys.argv[1] if len(sys.argv) > 1 else "work/swiftgram-src/ghostbase-final/GhostBase.ipa").resolve()
    # Materialized AppDelegate routing is verified immediately before Bazel by
    # verify_jerkgram_v12w_build133_runtime_repair1.py. Here we verify that the
    # packaged app still advertises every URL scheme needed to reach that code.
    verify_build140_identity(ipa)
    print("[Build140 final IPA verify] GREEN")
    print("[Build140 final IPA verify] com.jerkgram.ios / Telegram 12.9.2 / CFBundleVersion 140 / URL schemes jerkgram+telegram+tg")


if __name__ == "__main__":
    main()
