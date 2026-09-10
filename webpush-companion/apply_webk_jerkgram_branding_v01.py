#!/usr/bin/env python3
from pathlib import Path
import json
import re
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
VITE = ROOT / "vite.config.ts"
INDEX = ROOT / "index.html"
MANIFESTS = [ROOT / "public/site.webmanifest", ROOT / "public/site_apple.webmanifest"]

if not VITE.exists() or not INDEX.exists() or any(not path.exists() for path in MANIFESTS):
    raise SystemExit("[jerkgram-webk-branding] required Web K files not found")


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        if new in text:
            return text
        raise SystemExit(f"[jerkgram-webk-branding] missing {label} anchor")
    return text.replace(old, new, 1)


vite = VITE.read_text()
vite = replace_required(vite, "title: 'Telegram Web',", "title: 'Jerkgram Notifications',", "title")
vite = replace_required(
    vite,
    "description: 'Telegram is a cloud-based mobile and desktop messaging app with a focus on security and speed.',",
    "description: 'Notification companion for Jerkgram.',",
    "description",
)
# The companion is deployed to a user-selected dedicated HTTPS origin. Do not
# bake Telegram Web's production origin into generated metadata.
vite = replace_required(vite, "url: 'https://web.telegram.org/k/',", "url: '',", "url")
vite = replace_required(vite, "origin: 'https://web.telegram.org/'", "origin: ''", "origin")
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

# URL SEO metadata is irrelevant to an installed notification agent and causes
# Vite to treat relative placeholders as build assets. Remove it entirely; this
# also prevents the Telegram Web origin from ever leaking into the deployable.
html = re.sub(r'^\s*<meta property="(?:og|twitter):url"[^>]*>\s*\n?', '', html, flags=re.MULTILINE)
html = re.sub(r'^\s*<link rel="canonical"[^>]*>\s*\n?', '', html, flags=re.MULTILINE)
if "web.telegram.org" in html:
    raise SystemExit("[jerkgram-webk-branding] Telegram Web URL remains in index template")
INDEX.write_text(html)

for path in MANIFESTS:
    data = json.loads(path.read_text())
    data["name"] = "Jerkgram Notifications"
    data["short_name"] = "Jerkgram"
    data["id"] = "./"
    data["start_url"] = "./"
    data["scope"] = "./"
    data["description"] = "Notification companion for Jerkgram."

    icons = data.get("icons") or []
    compact_icons = [icon for icon in icons if icon.get("sizes") in {"192x192", "512x512"}]
    if compact_icons:
        data["icons"] = compact_icons

    for key in (
        "scope_extensions",
        "share_target",
        "screenshots",
        "shortcuts",
        "protocol_handlers",
        "related_applications",
        "prefer_related_applications",
        "gcm_sender_id",
    ):
        data.pop(key, None)

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

print("[jerkgram-webk-branding] OK")
