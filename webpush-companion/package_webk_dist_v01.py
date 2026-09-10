#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
PUBLIC = ROOT / "public"
DIST = ROOT / "dist"

if not PUBLIC.is_dir() or not DIST.is_dir():
    raise SystemExit("[jerkgram-webk-package] expected public/ and dist/")

# Jerkgram Notifications is not a general Telegram Web distribution. Vite has
# already emitted the JS/CSS/workers reachable from the companion entrypoint.
# Only copy public files that are needed for installation, notification display
# and the native handoff. In particular do not ship Web K emoji/TGS/audio/media
# catalogs, screenshots, stale generated bundles or source maps.
PUBLIC_ALLOWLIST = {
    "site.webmanifest",
    "site_apple.webmanifest",
    "open.html",
    "handoff.js",
    "assets/img/apple-touch-icon.png",
    "assets/img/favicon-16x16.png",
    "assets/img/favicon-32x32.png",
    "assets/img/favicon.ico",
    "assets/img/android-chrome-192x192.png",
    "assets/img/android-chrome-512x512.png",
    "assets/img/icon_square_192.png",
    "assets/img/icon_square_512.png",
    "assets/img/logo_filled_rounded.png",
    "assets/img/logo_plain.svg",
}

# The reduced auth/pairing shell still inherits a small amount of Web K CSS.
# Keep fonts only; all other public asset families are intentionally excluded.
PUBLIC_PREFIX_ALLOWLIST = (
    "assets/fonts/",
)

copied = 0
for source in PUBLIC.rglob("*"):
    if not source.is_file():
        continue
    rel = source.relative_to(PUBLIC).as_posix()
    if rel not in PUBLIC_ALLOWLIST and not rel.startswith(PUBLIC_PREFIX_ALLOWLIST):
        continue
    target = DIST / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    copied += 1

# Source maps expose far more of the upstream application than the deployed
# notification agent needs and are not required at runtime.
removed_maps = 0
for source_map in list(DIST.rglob("*.map")):
    source_map.unlink()
    removed_maps += 1

required = [
    DIST / "site.webmanifest",
    DIST / "site_apple.webmanifest",
    DIST / "open.html",
    DIST / "handoff.js",
    DIST / "assets/img/apple-touch-icon.png",
    DIST / "assets/img/logo_filled_rounded.png",
    DIST / "assets/img/logo_plain.svg",
]
missing = [str(path.relative_to(DIST)) for path in required if not path.exists()]
if missing:
    raise SystemExit("[jerkgram-webk-package] missing runtime assets: " + ", ".join(missing))

for forbidden in (
    DIST / "assets/img/screenshot.jpg",
    DIST / "assets/emoji",
    DIST / "assets/tgs",
    DIST / "assets/audio",
):
    if forbidden.exists():
        raise SystemExit(f"[jerkgram-webk-package] forbidden asset escaped filter: {forbidden.relative_to(DIST)}")

print(f"[jerkgram-webk-package] OK: copied {copied} public runtime assets; removed {removed_maps} source maps")
