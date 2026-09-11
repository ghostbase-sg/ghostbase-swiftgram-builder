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
    "tap-fallback.js",
    "push-tap-resolver.js",
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


def minimize_index_shell(index_path: Path) -> None:
    if not index_path.is_file():
        raise SystemExit("[jerkgram-webk-package] missing built index.html")

    text = index_path.read_text(encoding="utf-8")

    # Vite keeps Telegram Web K's dormant chat-list/sidebar HTML in index.html
    # even though the companion never boots appDialogsManager. Stock src/index.ts
    # still dereferences #page-chats and #main-columns on the signed-in path, so
    # retain only those two inert roots instead of deleting the container outright.
    legacy_start = '<div class="sidebar-left-overlay"></div>'
    legacy_end = '<div id="stories-viewer"></div>'
    minimal_shell = '''<div id="page-chats" style="display: none;">
      <div id="main-columns"></div>
    </div>'''

    if legacy_start in text:
        if text.count(legacy_start) != 1 or text.count(legacy_end) != 1:
            raise SystemExit("[jerkgram-webk-package] ambiguous Telegram chat shell in index.html")
        start = text.index(legacy_start)
        end = text.index(legacy_end, start) + len(legacy_end)
        text = text[:start] + minimal_shell + text[end:]
    elif 'id="page-chats"' not in text or 'id="main-columns"' not in text:
        raise SystemExit("[jerkgram-webk-package] required inert Web K startup roots missing")

    # Dead IE upgrade copy contains the only unrelated third-party navigation URL
    # in the built HTML. The iOS PWA cannot use it and should not ship it.
    ie_start = "<!--[if IE]>"
    ie_end = "<![endif]-->"
    if ie_start in text:
        if text.count(ie_start) != 1 or text.count(ie_end) != 1:
            raise SystemExit("[jerkgram-webk-package] ambiguous legacy IE block in index.html")
        start = text.index(ie_start)
        end = text.index(ie_end, start) + len(ie_end)
        text = text[:start] + text[end:]

    for required_root in ('id="page-chats"', 'id="main-columns"'):
        if text.count(required_root) != 1:
            raise SystemExit(f"[jerkgram-webk-package] startup root count changed: {required_root}")

    for forbidden in (
        "sidebar-left-overlay",
        "chatlist-container",
        "folders-container",
        "search-container",
        "column-left",
        "column-center",
        "column-right",
        "sidebar-search",
        "stories-viewer",
        "browsehappy.com",
    ):
        if forbidden in text:
            raise SystemExit(f"[jerkgram-webk-package] forbidden Telegram shell escaped index filter: {forbidden}")

    index_path.write_text(text, encoding="utf-8")


minimize_index_shell(DIST / "index.html")

required = [
    DIST / "index.html",
    DIST / "site.webmanifest",
    DIST / "site_apple.webmanifest",
    DIST / "open.html",
    DIST / "handoff.js",
    DIST / "tap-fallback.js",
    DIST / "push-tap-resolver.js",
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
    DIST / "push-open-bootstrap.js",
):
    if forbidden.exists():
        raise SystemExit(f"[jerkgram-webk-package] forbidden asset escaped filter: {forbidden.relative_to(DIST)}")

print(f"[jerkgram-webk-package] OK: copied {copied} public runtime assets; removed {removed_maps} source maps; minimized index shell")
