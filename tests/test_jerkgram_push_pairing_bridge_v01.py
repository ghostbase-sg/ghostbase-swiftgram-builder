from pathlib import Path
import subprocess
import sys


APP_DELEGATE = """class AppDelegate {\n    private let sharedContextPromise = Promise<SharedApplicationContext>()\n    var mainWindow: Window1?\n\n    private func handleJerkgramPushUrl(_ url: URL) -> Bool {\n        return false\n    }\n\n    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {\n        if self.handleJerkgramPushUrl(url) {\n            return true\n        }\n        self.openUrl(url: url)\n        return true\n    }\n}\n"""


def test_native_pairing_bridge_is_strict_account_aware_and_idempotent(tmp_path: Path):
    root = tmp_path / "telegram"
    app = root / "submodules/TelegramUI/Sources/AppDelegate.swift"
    app.parent.mkdir(parents=True)
    app.write_text(APP_DELEGATE)

    patcher = Path(__file__).parents[1] / "scripts/apply_jerkgram_push_pairing_bridge_v01.py"
    first = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert first.returncode == 0, first.stderr + first.stdout

    swift = app.read_text()
    assert 'private func handleJerkgramPushPairingUrl(_ url: URL) -> Bool' in swift
    assert 'url.scheme?.lowercased() == "jerkgram"' in swift
    assert 'url.host?.lowercased() == "push"' in swift
    assert 'url.path == "/authorize"' in swift
    assert 'url.absoluteString.utf8.count <= 2048' in swift
    assert 'rawToken.count <= 1536' in swift
    assert 'tokenData.count <= 1024' in swift

    # Query parsing must reject ambiguous duplicate token parameters rather than
    # silently accepting the first one.
    assert 'tokenItems.count == 1' in swift

    # Variant A: the Telegram account that is currently primary/active in Jerkgram.
    assert 'guard let primary = activeAccounts.primary else' in swift
    assert 'transaction.getPeer(primary.account.peerId)' in swift
    assert 'as? TelegramUser' in swift
    assert 'user?.username' in swift
    assert '[user.firstName, user.lastName]' in swift

    # Explicit confirmation must happen before Telegram's official accept wrapper.
    assert 'UIAlertController(' in swift
    assert 'Connect' in swift
    assert 'approveAuthTransferToken(' in swift
    assert 'primary.engine.privacy.activeSessions()' in swift
    assert swift.index('UIAlertController(') < swift.index('approveAuthTransferToken(')

    # Friendly states; no login token is logged or persisted.
    assert 'Connection request expired. Try again.' in swift
    assert 'Could not connect to Telegram. Try again.' in swift
    helper = swift[swift.index('private func handleJerkgramPushPairingUrl'):swift.index('func application(_ application: UIApplication, open url: URL')]
    assert 'UserDefaults' not in helper
    assert 'print(rawToken)' not in helper
    assert 'print(tokenData)' not in helper

    assert 'if self.handleJerkgramPushPairingUrl(url)' in swift
    assert swift.index('handleJerkgramPushPairingUrl(url)') < swift.index('handleJerkgramPushUrl(url)')

    # Security regression: only URL-safe base64 is accepted, and generic Telegram
    # URL handling happens only after both Jerkgram-owned handlers decline.
    assert 'case "A"..."Z", "a"..."z", "0"..."9", "-", "_"' in swift
    dispatch = swift[swift.index('func application(_ application: UIApplication, open url: URL'):]
    assert dispatch.index('handleJerkgramPushPairingUrl') < dispatch.index('handleJerkgramPushUrl') < dispatch.index('self.openUrl(url: url)')

    verifier = Path(__file__).parents[1] / "scripts/verify_jerkgram_push_pairing_bridge_v01.py"
    verified = subprocess.run([sys.executable, str(verifier), str(root)], capture_output=True, text=True)
    assert verified.returncode == 0, verified.stderr + verified.stdout
    assert "PASS" in verified.stdout

    second = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert second.returncode == 0, second.stderr + second.stdout
    swift2 = app.read_text()
    assert swift2.count('private func handleJerkgramPushPairingUrl(_ url: URL) -> Bool') == 1
    assert swift2.count('if self.handleJerkgramPushPairingUrl(url)') == 1
