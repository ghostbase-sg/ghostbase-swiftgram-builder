from pathlib import Path
import subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]

def callback_body(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth=0
    for i in range(brace, len(text)):
        if text[i]=='{': depth += 1
        elif text[i]=='}':
            depth -= 1
            if depth == 0: return text[brace+1:i]
    raise AssertionError('unclosed callback')

def test_all_telegram_external_url_entrypoints_route_jerkgram_before_generic_open():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); (root/'submodules/TelegramUI/Sources').mkdir(parents=True); (root/'Telegram/Telegram-iOS').mkdir(parents=True)
        app='''final class AppDelegate {\n    private var openUrlInProgress: URL?\n\n    func application(_ application: UIApplication, open url: URL, sourceApplication: String?) -> Bool {\n        self.openUrl(url: url)\n        return true\n    }\n\n    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {\n        self.openUrl(url: url)\n        return true\n    }\n\n    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool {\n        guard self.openUrlInProgress != url else {\n            return true\n        }\n        \n        self.openUrl(url: url)\n        return true\n    }\n}\n'''
        (root/'submodules/TelegramUI/Sources/AppDelegate.swift').write_text(app)
        plist='''\t\t<dict>\n\t\t\t<key>CFBundleTypeRole</key>\n\t\t\t<string>Viewer</string>\n\t\t\t<key>CFBundleURLName</key>\n\t\t\t<string>$(PRODUCT_BUNDLE_IDENTIFIER).compatibility</string>\n'''
        (root/'Telegram/Telegram-iOS/InfoBazel.plist').write_text(plist); (root/'Telegram/Telegram-iOS/Info.plist').write_text(plist)
        build='''        <dict>\n            <key>CFBundleTypeRole</key>\n            <string>Viewer</string>\n            <key>CFBundleURLName</key>\n            <string>{telegram_bundle_id}.compatibility</string>\n'''
        (root/'Telegram/BUILD').write_text(build)
        subprocess.run([sys.executable, ROOT/'scripts/apply_jerkgram_push_click_bridge_v01.py', root], check=True)
        subprocess.run([sys.executable, ROOT/'scripts/apply_jerkgram_push_pairing_bridge_v01.py', root], check=True)
        text=(root/'submodules/TelegramUI/Sources/AppDelegate.swift').read_text()
        signatures=[
          'func application(_ application: UIApplication, open url: URL, sourceApplication: String?) -> Bool',
          'func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool',
          'func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool',
        ]
        for sig in signatures:
            body=callback_body(text,sig)
            assert 'handleJerkgramExternalUrl(url)' in body
            assert body.index('handleJerkgramExternalUrl(url)') < body.index('self.openUrl(url: url)')
        modern=callback_body(text,signatures[2])
        assert modern.index('handleJerkgramExternalUrl(url)') < modern.index('guard self.openUrlInProgress != url') < modern.index('self.openUrl(url: url)')
        assert text.count('private func handleJerkgramPushPairingUrl(_ url: URL) -> Bool') == 1
        assert text.count('private func handleJerkgramPushUrl(_ url: URL) -> Bool') == 1
        assert text.count('private func handleJerkgramExternalUrl(_ url: URL) -> Bool') == 1
        dispatcher=callback_body(text,'private func handleJerkgramExternalUrl(_ url: URL) -> Bool')
        assert dispatcher.index('handleJerkgramPushPairingUrl(url)') < dispatcher.index('handleJerkgramPushUrl(url)')
        pairing=callback_body(text,'private func handleJerkgramPushPairingUrl(_ url: URL) -> Bool')
        assert 'url.path == "/authorize"' in pairing
        assert 'Consume every malformed authorize request locally' in pairing
        assert pairing.count('return true') >= 4
        assert 'print(rawToken)' not in pairing
        assert 'print(tokenData)' not in pairing
