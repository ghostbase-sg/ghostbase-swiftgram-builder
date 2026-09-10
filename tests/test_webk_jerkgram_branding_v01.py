from pathlib import Path
import json
import subprocess
import sys


def test_companion_branding_and_scope(tmp_path: Path):
    root = tmp_path / "tweb"
    public = root / "public"
    public.mkdir(parents=True)
    (root / "vite.config.ts").write_text(
        "context: {\n"
        "  title: 'Telegram Web',\n"
        "  description: 'Telegram is a cloud-based mobile and desktop messaging app with a focus on security and speed.',\n"
        "  url: 'https://web.telegram.org/k/',\n"
        "  origin: 'https://web.telegram.org/'\n"
        "}\n"
    )
    (root / "index.html").write_text(
        "<html><head>\n"
        "<title>Telegram Web</title>\n"
        "<meta name=\"description\" content=\"Telegram is a cloud-based mobile and desktop messaging app with a focus on security and speed.\">\n"
        "<meta name=\"mobile-web-app-title\" content=\"Telegram Web\">\n"
        "<meta name=\"apple-mobile-web-app-title\" content=\"Telegram Web\">\n"
        "<meta name=\"application-name\" content=\"Telegram Web\">\n"
        "<meta property=\"og:url\" content=\"https://web.telegram.org/k/\">\n"
        "<meta property=\"twitter:url\" content=\"https://web.telegram.org/k/\">\n"
        "<link rel=\"canonical\" href=\"https://web.telegram.org/\">\n"
        "</head></html>\n"
    )
    manifest = {
        "name": "Telegram Web",
        "short_name": "Telegram Web",
        "id": "/k/",
        "start_url": "./",
        "scope": "./",
        "scope_extensions": [{"type": "origin", "origin": "https://t.me"}],
        "share_target": {"action": "./share/"},
        "screenshots": [{"src": "assets/img/screenshot.jpg"}],
        "gcm_sender_id": "122867383838",
        "icons": [
            {"src": "assets/img/icon-36.png", "sizes": "36x36"},
            {"src": "assets/img/icon-192.png", "sizes": "192x192"},
            {"src": "assets/img/icon-512.png", "sizes": "512x512"},
        ],
        "display": "standalone",
    }
    for name in ("site.webmanifest", "site_apple.webmanifest"):
        (public / name).write_text(json.dumps(manifest))

    patcher = Path(__file__).parents[1] / "webpush-companion/apply_webk_jerkgram_branding_v01.py"
    result = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout

    vite = (root / "vite.config.ts").read_text()
    assert "title: 'Jerkgram Notifications'" in vite
    assert "Notification companion for Jerkgram." in vite
    assert "url: './'" in vite
    assert "origin: './'" in vite
    assert "web.telegram.org" not in vite

    html = (root / "index.html").read_text()
    assert "<title>Jerkgram Notifications</title>" in html
    assert 'content="Jerkgram Notifications"' in html
    assert "Notification companion for Jerkgram." in html
    assert "web.telegram.org" not in html

    for name in ("site.webmanifest", "site_apple.webmanifest"):
        data = json.loads((public / name).read_text())
        assert data["name"] == "Jerkgram Notifications"
        assert data["short_name"] == "Jerkgram"
        assert data["id"] == "./"
        assert data["scope"] == "./"
        assert {icon["sizes"] for icon in data["icons"]} == {"192x192", "512x512"}
        assert "scope_extensions" not in data
        assert "share_target" not in data
        assert "screenshots" not in data
        assert "gcm_sender_id" not in data
