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
        "}\n"
    )
    manifest = {
        "name": "Telegram Web",
        "short_name": "Telegram Web",
        "id": "/k/",
        "start_url": "./",
        "scope": "./",
        "scope_extensions": [{"type": "origin", "origin": "https://t.me"}],
        "share_target": {"action": "./share/"},
        "icons": [],
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

    for name in ("site.webmanifest", "site_apple.webmanifest"):
        data = json.loads((public / name).read_text())
        assert data["name"] == "Jerkgram Notifications"
        assert data["short_name"] == "Jerkgram"
        assert data["id"] == "./"
        assert data["scope"] == "./"
        assert "scope_extensions" not in data
        assert "share_target" not in data
