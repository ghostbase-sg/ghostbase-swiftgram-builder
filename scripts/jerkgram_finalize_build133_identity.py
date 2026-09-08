#!/usr/bin/env python3

from pathlib import Path
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

import jerkgram_finalize_build130_identity as base


BUILD = "136"
PUBLIC_BUNDLE = "com.jerkgram.ios"
OLD_PUBLIC_BUNDLE = "ph.telegra.Telegraph"
PUBLIC_TEAM = "C67CF9S4VU"
PUBLIC_GROUP = "group.com.jerkgram.ios"
TELEGRAM_VERSION = "12.9.2"
JERKGRAM_DISPLAY_VERSION = "1.0.2 Beta 2"
JERKGRAM_TECHNICAL_VERSION = "1.0.2-beta.2"

# The last-good run 34040990849 is the release identity baseline:
# Telegram 12.9.2 / Jerkgram display name; Build136 preserves the public bundle.
# Keep that exact public identity and advance only Build/Jerkgram release data.
base.base.base.BUILD = BUILD

EXTENSION_SUFFIXES = {
    "BroadcastUploadExtension.appex": "BroadcastUpload",
    "IntentsExtension.appex": "SiriIntents",
    "NotificationContentExtension.appex": "NotificationContent",
    "NotificationServiceExtensionv1.appex": "NotificationService",
    "ShareExtension.appex": "Share",
    "WidgetExtension.appex": "Widget",
}
KEYCHAIN_EXTENSIONS = {
    "BroadcastUploadExtension.appex",
    "IntentsExtension.appex",
    "WidgetExtension.appex",
}


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build136 identity] " + message)


def load_plist(path: Path):
    with path.open("rb") as file:
        return plistlib.load(file)


def save_plist(path: Path, value) -> None:
    original = path.read_bytes()
    fmt = plistlib.FMT_BINARY if original.startswith(b"bplist") else plistlib.FMT_XML
    path.write_bytes(plistlib.dumps(value, fmt=fmt, sort_keys=False))


def rewrite_bundle_identifiers(root: Path) -> list[Path]:
    apps = list((root / "Payload").glob("*.app"))
    require(len(apps) == 1, "expected exactly one main app")
    app = apps[0]
    main_info_path = app / "Info.plist"
    main_info = load_plist(main_info_path)
    require(main_info.get("CFBundleIdentifier") == OLD_PUBLIC_BUNDLE, "unexpected pre-Build134 main bundle")
    main_info["CFBundleIdentifier"] = PUBLIC_BUNDLE
    save_plist(main_info_path, main_info)

    plugins = {path.name: path for path in (app / "PlugIns").glob("*.appex") if path.is_dir()}
    require(set(plugins) == set(EXTENSION_SUFFIXES), "extension topology mismatch")
    changed = [main_info_path]
    for name, suffix in EXTENSION_SUFFIXES.items():
        info_path = plugins[name] / "Info.plist"
        info = load_plist(info_path)
        require(info.get("CFBundleIdentifier") == OLD_PUBLIC_BUNDLE + "." + suffix, f"unexpected pre-Build134 bundle for {name}")
        info["CFBundleIdentifier"] = PUBLIC_BUNDLE + "." + suffix
        save_plist(info_path, info)
        changed.append(info_path)
    return changed


def carrier_entitlements(bundle_id: str, *, main: bool, keychain: bool):
    value = {
        "application-identifier": f"{PUBLIC_TEAM}.{bundle_id}",
        "com.apple.security.application-groups": [PUBLIC_GROUP],
        "get-task-allow": False,
    }
    if main:
        value["aps-environment"] = "production"
    elif keychain:
        value["com.apple.developer.team-identifier"] = PUBLIC_TEAM
        value["keychain-access-groups"] = [f"{PUBLIC_TEAM}.*", "com.apple.token"]
    else:
        value["aps-environment"] = "production"
    return value


def sign_carrier(executable: Path, entitlements, root: Path) -> None:
    codesign = shutil.which("codesign")
    require(codesign is not None, "codesign missing")
    entitlement_path = root / (executable.name + ".build134.entitlements.plist")
    entitlement_path.write_bytes(plistlib.dumps(entitlements, fmt=plistlib.FMT_XML, sort_keys=False))
    result = subprocess.run(
        [codesign, "--force", "--sign", "-", "--timestamp=none", "--generate-entitlement-der", "--entitlements", str(entitlement_path), str(executable)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(result.returncode == 0, f"ad-hoc carrier signing failed for {executable.name}: {result.stderr}")


def rebase_ipa_namespace(ipa: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="jerkgram-build134-identity-") as directory:
        root = Path(directory)
        with zipfile.ZipFile(ipa, "r") as archive:
            infos = archive.infolist()
            archive.extractall(root)

        changed = set(rewrite_bundle_identifiers(root))
        app = next((root / "Payload").glob("*.app"))
        bundles = [(app, True, False)]
        for name in EXTENSION_SUFFIXES:
            bundles.append((app / "PlugIns" / name, False, name in KEYCHAIN_EXTENSIONS))

        for bundle, is_main, is_keychain in bundles:
            info = load_plist(bundle / "Info.plist")
            executable = bundle / info["CFBundleExecutable"]
            require(executable.is_file(), f"executable missing for {bundle.name}")
            profile = bundle / "embedded.mobileprovision"
            if profile.exists():
                profile.unlink()
            signature = bundle / "_CodeSignature"
            if signature.exists():
                shutil.rmtree(signature)
            sign_carrier(
                executable,
                carrier_entitlements(info["CFBundleIdentifier"], main=is_main, keychain=is_keychain),
                root,
            )
            changed.add(executable)

        modified = {path.relative_to(root).as_posix(): path.read_bytes() for path in changed}
        fd, temp_name = tempfile.mkstemp(prefix=ipa.name + ".build134.", suffix=".tmp", dir=str(ipa.parent))
        os.close(fd)
        temp = Path(temp_name)
        try:
            with zipfile.ZipFile(ipa, "r") as source, zipfile.ZipFile(temp, "w") as output:
                for info in infos:
                    member = info.filename
                    if member.endswith("/embedded.mobileprovision") or "/_CodeSignature/" in member:
                        continue
                    data = modified[member] if member in modified else source.read(info)
                    output.writestr(info, data)
            os.replace(temp, ipa)
        finally:
            if temp.exists():
                temp.unlink()


def main() -> None:
    ipa = Path(sys.argv[1] if len(sys.argv) > 1 else "work/swiftgram-src/ghostbase-final/GhostBase.ipa").resolve()
    base.main()
    rebase_ipa_namespace(ipa)
    print("[Build136 identity] GREEN")
    print("[Build136 identity] com.jerkgram.ios / CFBundleShortVersionString=12.9.2 / CFBundleVersion=136")
    print("[Build136 identity] in-app Jerkgram release: 1.0.2 Beta 2 (1.0.2-beta.2)")


if __name__ == "__main__":
    main()
