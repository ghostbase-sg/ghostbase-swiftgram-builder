#!/usr/bin/env python3
"""Verify Build137 phase-two hot-settings and invalidation contracts."""
import apply_jerkgram_build137_performance2 as patch


def require(value, message):
    if not value:
        raise RuntimeError("[Build137 performance2 verify] " + message)


def main():
    account = patch.base.ACCOUNT.read_text()
    require(account.count(patch.MARKER) == 1, "hot settings owner count")
    require("public static let keys: Set<String>" in account, "allowlist missing")
    require("precondition(self.keys.contains(key))" in account, "unbounded key access")
    require("private static var snapshot: [String: Any]?" in account, "snapshot missing")
    activity = patch.base.function_block(account, "private static func settings() -> JerkgramActivityGhostSettings")
    require("return self.cached.modify" in activity, "activity load is not atomic with publication")
    require("cached.with" not in activity, "racy activity pre-read survived")

    policy = patch.base.BLOCKED_POLICY.read_text()
    blocked = patch.base.function_block(policy, "private static func settings(accountPeerId: PeerId)")
    require("let result = self.settingsByAccount.modify" in blocked, "blocked settings load is not atomic")
    require("settingsByAccount.with" not in blocked, "racy blocked settings pre-read survived")

    chat_list = patch.base.CHAT_LIST.read_text()
    require("case .Generic, .FillHole:" in chat_list, "history mutation invalidation missing")
    require("!mustRefreshFallback" in chat_list, "fallback cache ignores history mutations")

    glass = patch.base.GLASS.read_text()
    reload_block = patch.base.function_block(glass, "public static func reloadFromDefaults()")
    require("enabledLock.lock()" in reload_block, "Glass reload is not locked")
    require("UserDefaults.standard.object" in reload_block, "Glass reload does not refresh value")

    root = patch.base.RAM_ROOT.read_text()
    theme = patch.base.function_block(root, "override public func containerLayoutUpdated(")
    require("ghostBaseUpdateRamValue()" not in theme, "RAM sampling returned to layout")
    require("ghostBaseUpdateRamOverlayState()" not in theme, "RAM defaults read returned to layout")
    require("ghostBaseRamLabel?.textColor" in root, "RAM label does not follow theme")
    require("timer.tolerance" in root, "RAM timer tolerance missing")

    for owner, signature in (
        (patch.base.SHARED_ACCOUNT_CONTEXT, "private func jerkgramBuild135ProjectAccountSettings("),
        (patch.ARCHIVE, "private func jerkgramProjectImportedSettingsToActiveDefaults("),
    ):
        block = patch.base.function_block(owner.read_text(), signature)
        for required in ("JerkgramHotSettings.invalidate()", "JerkgramActivityGhostRuntime.invalidate()",
                         "JerkgramBlockedReactionPolicy.notifySettingsChanged()",
                         "GhostBaseGlassStyle.reloadFromDefaults()", patch.base.RAM_NOTIFICATION):
            require(required in block, f"projection refresh missing: {required}")

    settings = patch.base.SETTINGS.read_text()
    persist = patch.base.function_block(settings, "private func jerkgramPersistChangedSettings(")
    require("Set<String>([" in persist and "]).union(JerkgramHotSettings.keys)" in persist,
            "cached settings are not combined as a Swift Set")
    require("defer { JerkgramHotSettings.invalidate() }" in persist, "settings snapshot invalidation missing")

    supported_reads = 0
    for module in patch.MODULES:
        for path in (patch.ROOT / "submodules" / module).rglob("*.swift"):
            text = path.read_text()
            supported_reads += text.count("JerkgramHotSettings.object(forKey:")
            for match in patch.READ.finditer(text):
                require(match.group(2) not in patch.KEYS, f"uncached supported read: {path}")
    require(supported_reads > 20, "too few hot reads were rewritten")
    require("jerkgram.READ3." not in patch.READ_STATS.read_text(), "READ3 diagnostics survived")
    require("V10T.SendTextStyleApplied.Count" not in patch.CHAT_CONTROLLER.read_text(), "send diagnostics survived")
    source_probe = patch.base.function_block(patch.CHAT_LOAD.read_text(), "private func ghostBaseV10NSaveSourcePeerId(")
    require("UserDefaults.standard" not in source_probe, "source-peer diagnostic persistence survived")
    print("[Build137 performance2 verify] GREEN")


if __name__ == "__main__":
    main()
