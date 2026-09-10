#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
VITE = ROOT / "vite.config.ts"
INDEX = ROOT / "index.html"
MANIFESTS = [ROOT / "public/site.webmanifest", ROOT / "public/site_apple.webmanifest"]

if not VITE.exists() or not INDEX.exists() or any(not path.exists() for path in MANIFESTS):
    raise SystemExit("[jerkgram-webk-branding] required Web K files not found")

vite = VITE.read_text()
vite = vite.replace("title: 'Telegram Web',", "title: 'Jerkgram Notifications',", 1)
vite = vite.replace(
    "description: 'Telegram is a cloud-based mobile and desktop messaging app with a focus on security and speed.',",
    "description: 'Notification companion for Jerkgram.',",
    1,
)
VITE.write_text(vite)

html = INDEX.read_text()
html = html.replace("<title>Telegram Web</title>", "<title>Jerkgram Notifications</title>")
html = html.replace(
    'content="Telegram is a cloud-based mobile and desktop messaging app with a focus on security and speed."',
    'content="Notification companion for Jerkgram."',
)
html = html.replace('content="Telegram Web"', 'content="Jerkgram Notifications"')
html = html.replace('href="https://web.telegram.org/"', 'href="./"')
html = html.replace('content="https://web.telegram.org/k/"', 'content="./"')
INDEX.write_text(html)

for path in MANIFESTS:
    data = json.loads(path.read_text())
    data["name"] = "Jerkgram Notifications"
    data["short_name"] = "Jerkgram"
    # A relative identity keeps this companion scoped to whichever dedicated
    # HTTPS origin/path it is deployed under instead of claiming Telegram Web /k/.
    data["id"] = "./"
    data["start_url"] = "./"
    data["scope"] = "./"
    data["description"] = "Notification companion for Jerkgram."
    # This agent should never claim t.me/telegram.me navigation or OS share
    # targets. Its only user-facing jobs are pairing and notifications.
    data.pop("scope_extensions", None)
    data.pop("share_target", None)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

print("[jerkgram-webk-branding] OK")
