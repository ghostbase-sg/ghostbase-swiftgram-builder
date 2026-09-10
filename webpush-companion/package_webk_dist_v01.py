#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
PUBLIC = ROOT / "public"
DIST = ROOT / "dist"

if not PUBLIC.is_dir() or not DIST.is_dir():
    raise SystemExit("[jerkgram-webk-package] expected public/ and dist/")

# Telegram Web K pins build.copyPublicDir=false because public/ may contain stale
# generated JS bundles. Mirror its keepAsset.js policy instead of copying public/
# wholesale, then add the two Jerkgram-owned handoff files explicitly.
def keep_webk_asset(rel: str) -> bool:
    return (
        ".xml" in rel
        or "version" in rel
        or "assets/" in rel
        or "changelogs/" in rel
        or ".webmanifest" in rel
        or "Worker.min.wasm" in rel
        or "Worker.min.js" in rel
        or "recorder.min.js" in rel
        or "snapshot.html" in rel
        or ".hbs" in rel
    )

copied = 0
for source in PUBLIC.rglob("*"):
    if not source.is_file():
        continue
    rel = source.relative_to(PUBLIC).as_posix()
    if not (keep_webk_asset(rel) or rel in {"open.html", "handoff.js"}):
        continue
    target = DIST / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    copied += 1

required = [
    DIST / "site.webmanifest",
    DIST / "site_apple.webmanifest",
    DIST / "open.html",
    DIST / "handoff.js",
    DIST / "assets/img/apple-touch-icon.png",
]
missing = [str(path.relative_to(DIST)) for path in required if not path.exists()]
if missing:
    raise SystemExit("[jerkgram-webk-package] missing runtime assets: " + ", ".join(missing))

print(f"[jerkgram-webk-package] OK: copied {copied} filtered runtime assets")
