from pathlib import Path
import subprocess
import sys


APP_DELEGATE = """class AppDelegate {\n    private let sharedContextPromise = Promise<SharedApplicationContext>()\n    var mainWindow: Window1?\n\n    private func handleJerkgramPushUrl(_ url: URL) -> Bool {\n        return false\n    }\n\n    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {\n        if self.handleJerkgramPushUrl(url) {\n            return true\n        }\n        self.openUrl(url: url)\n        return true\n    }\n}\n"""


def test_native_pairing_bridge_is_bounded_and_idempotent(tmp_path: Path):
    root = tmp_path / "telegram"
    app = root / "submodules/TelegramUI/Sources/AppDelegate.swift"
    app.parent.mkdir(parents=True)
    app.write_text(APP_DELEGATE)

    patcher = Path(__file__).parents[1] / "scripts/apply_jerkgram_push_pairing_bridge_v01.py"
    first = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert first.returncode == 0, first.stderr + first.stdout

    swift = app.read_text()
    assert 'private func handleJerkgramPushPairingUrl(_ url: URL) -> Bool' in swift
    assert 'url.path == "/authorize"' in swift
    assert 'rawToken.count <= 1536' in swift
    assert 'tokenData.count <= 1024' in swift
    assert 'approveAuthTransferToken(' in swift
    assert 'primary.engine.privacy.activeSessions()' in swift
    assert 'Connect this Telegram account to Jerkgram Notifications?' in swift
    assert 'if self.handleJerkgramPushPairingUrl(url)' in swift
    assert swift.index('handleJerkgramPushPairingUrl(url)') < swift.index('handleJerkgramPushUrl(url)')

    # Security regression: only URL-safe base64 is accepted, and generic Telegram
    # URL handling happens only after both Jerkgram-owned handlers decline.
    assert 'case "A"..."Z", "a"..."z", "0"..."9", "-", "_"' in swift
    dispatch = swift[swift.index('func application(_ application: UIApplication, open url: URL'):]
    assert dispatch.index('handleJerkgramPushPairingUrl') < dispatch.index('handleJerkgramPushUrl') < dispatch.index('self.openUrl(url: url)')

    second = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert second.returncode == 0, second.stderr + second.stdout
    swift2 = app.read_text()
    assert swift2.count('private func handleJerkgramPushPairingUrl(_ url: URL) -> Bool') == 1
    assert swift2.count('if self.handleJerkgramPushPairingUrl(url)') == 1
