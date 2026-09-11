from pathlib import Path
import subprocess
import sys


def test_companion_packaging_is_notification_only(tmp_path: Path):
    root = tmp_path / "tweb"
    public = root / "public"
    dist = root / "dist"
    (public / "assets/img").mkdir(parents=True)
    (public / "assets/fonts").mkdir(parents=True)
    (public / "assets/emoji").mkdir(parents=True)
    (public / "assets/tgs").mkdir(parents=True)
    (public / "assets/audio").mkdir(parents=True)
    dist.mkdir(parents=True)

    (public / "site.webmanifest").write_text("{}")
    (public / "site_apple.webmanifest").write_text("{}")
    (public / "open.html").write_text("open")
    (public / "handoff.js").write_text("handoff")
    (public / "tap-fallback.js").write_text("tap fallback")
    (public / "push-tap-resolver.js").write_text("tap resolver")
    for name in (
        "apple-touch-icon.png",
        "favicon-16x16.png",
        "favicon-32x32.png",
        "favicon.ico",
        "android-chrome-192x192.png",
        "android-chrome-512x512.png",
        "icon_square_192.png",
        "icon_square_512.png",
        "logo_filled_rounded.png",
        "logo_plain.svg",
    ):
        (public / "assets/img" / name).write_bytes(b"asset")

    (public / "assets/fonts/tgico.woff").write_bytes(b"font")
    (public / "assets/img/other.png").write_bytes(b"drop")
    (public / "assets/img/screenshot.jpg").write_bytes(b"drop")
    (public / "assets/emoji/emoji.png").write_bytes(b"drop")
    (public / "assets/tgs/animation.tgs").write_bytes(b"drop")
    (public / "assets/audio/sound.mp3").write_bytes(b"drop")
    (public / "push-open-bootstrap.js").write_text("legacy drop")
    (public / "STALE-BUNDLE.js").write_text("drop")
    (dist / "app-123.js").write_text("keep built runtime")
    (dist / "app-123.js.map").write_text("drop map")
    (dist / "index.html").write_text(
        '''<!doctype html>
<html>
<body>
<!--[if IE]><p class="browserupgrade"><a href="https://browsehappy.com/">upgrade</a></p><![endif]-->
<div class="sidebar-left-overlay"></div>
<div class="whole page-chats" style="display: none;" id="page-chats">
  <div id="main-columns" class="tabs-container" data-animation="navigation">
    <div class="tabs-tab chatlist-container sidebar sidebar-left main-column" id="column-left">
      <div id="folders-container"></div>
      <div class="sidebar-search" id="search-container"></div>
    </div>
    <div class="tabs-tab main-column" id="column-center"></div>
    <div class="tabs-tab sidebar sidebar-right main-column" id="column-right"></div>
  </div>
</div>
<div id="stories-viewer"></div>
</body>
</html>
'''
    )

    packager = Path(__file__).parents[1] / "webpush-companion/package_webk_dist_v01.py"
    result = subprocess.run([sys.executable, str(packager), str(root)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout

    assert (dist / "app-123.js").exists()
    assert not (dist / "app-123.js.map").exists()
    assert (dist / "site.webmanifest").exists()
    assert (dist / "site_apple.webmanifest").exists()
    assert (dist / "open.html").exists()
    assert (dist / "handoff.js").exists()
    assert (dist / "tap-fallback.js").exists()
    assert (dist / "push-tap-resolver.js").exists()
    assert not (dist / "push-open-bootstrap.js").exists()
    assert (dist / "assets/img/apple-touch-icon.png").exists()
    assert (dist / "assets/img/logo_filled_rounded.png").exists()
    assert (dist / "assets/img/logo_plain.svg").exists()
    assert (dist / "assets/fonts/tgico.woff").exists()

    assert not (dist / "assets/img/other.png").exists()
    assert not (dist / "assets/img/screenshot.jpg").exists()
    assert not (dist / "assets/emoji").exists()
    assert not (dist / "assets/tgs").exists()
    assert not (dist / "assets/audio").exists()
    assert not (dist / "STALE-BUNDLE.js").exists()

    # Keep only the two inert DOM roots that stock Web K's startup expects.
    html = (dist / "index.html").read_text()
    assert 'id="page-chats"' in html
    assert 'id="main-columns"' in html
    assert 'style="display: none;"' in html
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
        assert forbidden not in html
