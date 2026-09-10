from pathlib import Path
import subprocess
import sys


PLIST = """<plist>\n<array>\n\t\t<dict>\n\t\t\t<key>CFBundleTypeRole</key>\n\t\t\t<string>Viewer</string>\n\t\t\t<key>CFBundleURLName</key>\n\t\t\t<string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>\n\t\t\t<key>CFBundleURLSchemes</key>\n\t\t\t<array>\n\t\t\t\t<string>telegram</string>\n\t\t\t</array>\n\t\t</dict>\n\t\t<dict>\n\t\t\t<key>CFBundleTypeRole</key>\n\t\t\t<string>Viewer</string>\n\t\t\t<key>CFBundleURLName</key>\n\t\t\t<string>$(PRODUCT_BUNDLE_IDENTIFIER).compatibility</string>\n\t\t\t<key>CFBundleURLSchemes</key>\n\t\t\t<array>\n\t\t\t\t<string>tg</string>\n\t\t\t\t<string>$(APP_SPECIFIC_URL_SCHEME)</string>\n\t\t\t</array>\n\t\t</dict>\n</array>\n</plist>\n"""

BUILD = """        <dict>\n            <key>CFBundleTypeRole</key>\n            <string>Viewer</string>\n            <key>CFBundleURLName</key>\n            <string>{telegram_bundle_id}</string>\n            <key>CFBundleURLSchemes</key>\n            <array>\n                <string>telegram</string>\n            </array>\n        </dict>\n        <dict>\n            <key>CFBundleTypeRole</key>\n            <string>Viewer</string>\n            <key>CFBundleURLName</key>\n            <string>{telegram_bundle_id}.compatibility</string>\n            <key>CFBundleURLSchemes</key>\n            <array>\n                <string>tg</string>\n            </array>\n        </dict>\n"""

APP_DELEGATE = """class AppDelegate {\n    private let sharedContextPromise = Promise<SharedApplicationContext>()\n    private func openChatWhenReady(accountId: AccountRecordId?, peerId: PeerId, threadId: Int64?, messageId: MessageId? = nil, activateInput: Bool = false, storyId: StoryId?, openAppIfAny: Bool = false, alwaysKeepMessageId: Bool = false) {}\n\n    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {\n        self.openUrl(url: url)\n        return true\n    }\n}\n"""


def write_fixture(root: Path):
    app = root / "submodules/TelegramUI/Sources/AppDelegate.swift"
    info_bazel = root / "Telegram/Telegram-iOS/InfoBazel.plist"
    info = root / "Telegram/Telegram-iOS/Info.plist"
    build = root / "Telegram/BUILD"
    for p in (app, info_bazel, info, build):
        p.parent.mkdir(parents=True, exist_ok=True)
    app.write_text(APP_DELEGATE)
    info_bazel.write_text(PLIST)
    info.write_text(PLIST)
    build.write_text(BUILD)
    return app, info_bazel, info, build


def test_push_click_bridge_is_bounded_and_idempotent(tmp_path: Path):
    root = tmp_path / "telegram"
    app, info_bazel, info, build = write_fixture(root)
    patcher = Path(__file__).parents[1] / "scripts/apply_jerkgram_push_click_bridge_v01.py"

    first = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert first.returncode == 0, first.stderr + first.stdout

    swift = app.read_text()
    assert 'private func handleJerkgramPushUrl(_ url: URL) -> Bool' in swift
    assert 'url.scheme?.lowercased() == "jerkgram"' in swift
    assert 'url.host?.lowercased() == "push"' in swift
    assert 'case "user"' in swift and 'CloudUser' in swift
    assert 'case "chat"' in swift and 'CloudGroup' in swift
    assert 'case "channel"' in swift and 'CloudChannel' in swift
    assert 'self.openChatWhenReady(' in swift
    assert 'alwaysKeepMessageId: true' in swift
    assert 'if self.handleJerkgramPushUrl(url)' in swift

    for plist in (info_bazel, info):
        text = plist.read_text()
        assert text.count('<string>jerkgram</string>') == 1
        assert '<string>telegram</string>' in text
        assert '<string>tg</string>' in text

    build_text = build.read_text()
    assert build_text.count('<string>jerkgram</string>') == 1
    assert '<string>telegram</string>' in build_text
    assert '<string>tg</string>' in build_text

    second = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert second.returncode == 0, second.stderr + second.stdout
    assert app.read_text().count('private func handleJerkgramPushUrl(_ url: URL) -> Bool') == 1
    assert info_bazel.read_text().count('<string>jerkgram</string>') == 1
    assert build.read_text().count('<string>jerkgram</string>') == 1
