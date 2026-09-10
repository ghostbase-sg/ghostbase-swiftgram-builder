from pathlib import Path
import subprocess
import sys


def test_companion_packaging_filters_public_assets(tmp_path: Path):
    root = tmp_path / "tweb"
    public = root / "public"
    dist = root / "dist"
    (public / "assets/img").mkdir(parents=True)
    dist.mkdir(parents=True)

    (public / "site.webmanifest").write_text("{}")
    (public / "site_apple.webmanifest").write_text("{}")
    (public / "open.html").write_text("open")
    (public / "handoff.js").write_text("handoff")
    (public / "assets/img/apple-touch-icon.png").write_bytes(b"png")
    (public / "assets/img/other.png").write_bytes(b"png2")
    (public / "browserconfig.xml").write_text("xml")
    (public / "STALE-BUNDLE.js").write_text("must not ship")
    (public / "STALE-BUNDLE.js.map").write_text("must not ship")

    packager = Path(__file__).parents[1] / "webpush-companion/package_webk_dist_v01.py"
    result = subprocess.run([sys.executable, str(packager), str(root)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout

    assert (dist / "site.webmanifest").exists()
    assert (dist / "site_apple.webmanifest").exists()
    assert (dist / "open.html").exists()
    assert (dist / "handoff.js").exists()
    assert (dist / "assets/img/apple-touch-icon.png").exists()
    assert (dist / "assets/img/other.png").exists()
    assert (dist / "browserconfig.xml").exists()
    assert not (dist / "STALE-BUNDLE.js").exists()
    assert not (dist / "STALE-BUNDLE.js.map").exists()
