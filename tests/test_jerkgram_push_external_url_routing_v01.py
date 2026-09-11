#!/usr/bin/env python3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APPLY = REPO / "scripts" / "apply_jerkgram_push_pairing_bridge_v01.py"
VERIFY = REPO / "scripts" / "verify_jerkgram_push_pairing_bridge_v01.py"

SOURCE_ONLY = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?) -> Bool {
        self.openUrl(url: url)
        return true
    }
"""

ANNOTATION_CLICK_ONLY = """    func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool {
        if self.handleJerkgramPushUrl(url) {
            return true
        }
        self.openUrl(url: url)
        return true
    }
"""

MODERN = """    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool {
        guard self.openUrlInProgress != url else {
            return true
        }
        
        self.openUrl(url: url)
        return true
    }
"""

CLICK_HELPER = """    private func handleJerkgramPushUrl(_ url: URL) -> Bool {
        guard url.scheme?.lowercased() == "jerkgram" else {
            return false
        }
        guard url.host?.lowercased() == "push", url.path == "/open" else {
            return true
        }
        self.openChatWhenReady(
            accountId: nil,
            peerId: PeerId(namespace: Namespaces.Peer.CloudUser, id: PeerId.Id._internalFromInt64Value(1)),
            threadId: nil,
            messageId: nil,
            storyId: nil,
            alwaysKeepMessageId: true
        )
        return true
    }

"""

def callback_scope(text: str, signature: str) -> str:
    start = text.index(signature)
    body_start = text.index("{", start)
    depth = 0
    for index in range(body_start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise AssertionError(f"unterminated callback: {signature}")

class ExternalUrlRoutingTests(unittest.TestCase):
    def materialize(self) -> str:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app = root / "submodules/TelegramUI/Sources/AppDelegate.swift"
            app.parent.mkdir(parents=True)
            app.write_text(
                "final class AppDelegate {\n"
                + CLICK_HELPER
                + SOURCE_ONLY
                + "\n"
                + ANNOTATION_CLICK_ONLY
                + "\n"
                + MODERN
                + "}\n"
            )
            subprocess.check_call([sys.executable, str(APPLY), str(root)])
            subprocess.check_call([sys.executable, str(VERIFY), str(root)])
            return app.read_text()

    def test_all_three_external_url_callbacks_use_unified_jerkgram_dispatch(self):
        text = self.materialize()
        signatures = [
            "func application(_ application: UIApplication, open url: URL, sourceApplication: String?) -> Bool",
            "func application(_ application: UIApplication, open url: URL, sourceApplication: String?, annotation: Any) -> Bool",
            "func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool",
        ]
        for signature in signatures:
            scope = callback_scope(text, signature)
            self.assertEqual(scope.count("self.handleJerkgramExternalUrl(url)"), 1, signature)
            self.assertLess(scope.index("self.handleJerkgramExternalUrl(url)"), scope.index("self.openUrl(url: url)"), signature)

    def test_modern_callback_preserves_open_url_in_progress_after_jerkgram_dispatch(self):
        text = self.materialize()
        signature = "func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool"
        scope = callback_scope(text, signature)
        self.assertLess(scope.index("self.handleJerkgramExternalUrl(url)"), scope.index("guard self.openUrlInProgress != url"))
        self.assertLess(scope.index("guard self.openUrlInProgress != url"), scope.index("self.openUrl(url: url)"))

    def test_unified_dispatch_prioritizes_authorize_then_open(self):
        text = self.materialize()
        marker = "private func handleJerkgramExternalUrl(_ url: URL) -> Bool"
        start = text.index(marker)
        end = text.index("\n    func application(", start)
        scope = text[start:end]
        self.assertLess(scope.index("self.handleJerkgramPushPairingUrl(url)"), scope.index("self.handleJerkgramPushUrl(url)"))
        self.assertNotIn("self.openUrl(url: url)", scope)

    def test_invalid_authorize_is_consumed_before_generic_router(self):
        text = self.materialize()
        marker = "private func handleJerkgramPushPairingUrl(_ url: URL) -> Bool"
        start = text.index(marker)
        end = text.index("private func handleJerkgramExternalUrl", start)
        scope = text[start:end]
        route_guard = 'url.path == "/authorize" else'
        validation_guard = "guard url.absoluteString.utf8.count <= 2048"
        self.assertIn(route_guard, scope)
        self.assertIn(validation_guard, scope)
        self.assertLess(scope.index(route_guard), scope.index(validation_guard))
        post_route = scope[scope.index(validation_guard):]
        self.assertIn("return true", post_route)

if __name__ == "__main__":
    unittest.main()
