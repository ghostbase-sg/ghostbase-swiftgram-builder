#!/usr/bin/env python3
"""Late runtime settings snapshot; preserves caller fallbacks and feature policy."""
import re
import apply_jerkgram_v12zd_build137_performance1 as base

ROOT = base.ROOT
KEYS = (
    "jerkgram.GhostMode.ScheduledSend",
    "jerkgram.Messages.SendTextStyle",
    "jerkgram.Messages.ShowDeleted",
    "jerkgram.Messages.ShowEditHistory",
) + tuple("jerkgram.ProtectedContent." + key for key in (
    "AllowScreenRecording", "AllowScreenshots", "ChatCopy", "ChatForward",
    "ChatSave", "Enabled", "GalleryCopy", "GallerySave", "GalleryShare",
    "OneTimeSave", "OneTimeScreenRecording", "OneTimeScreenshots",
))
MODULES = ("TelegramCore", "TelegramUI", "GalleryUI", "ShareController", "ChatListUI")
ARCHIVE = ROOT / "submodules/SettingsUI/Sources/Jerkgram/JerkgramArchiveFlowController.swift"
CHAT_LOAD = ROOT / "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift"
CHAT_CONTROLLER = ROOT / "submodules/TelegramUI/Sources/ChatController.swift"
READ_STATS = ROOT / "submodules/TelegramCore/Sources/TelegramEngine/Messages/MessageReadStats.swift"
READ = re.compile(r'UserDefaults\.standard\.(object|string)\(\s*forKey:\s*"([^"]+)"\s*\)')
MARKER = "// MARK: Jerkgram BUILD137_HOT_SETTINGS2"
RUNTIME = MARKER + '''
public enum JerkgramHotSettings {
    public static let keys: Set<String> = [
''' + "".join('        "' + key + '",\n' for key in KEYS) + '''    ]
    private static let lock = NSLock()
    private static var snapshot: [String: Any]?

    public static func invalidate() {
        self.lock.lock()
        self.snapshot = nil
        self.lock.unlock()
    }

    public static func object(forKey key: String) -> Any? {
        precondition(self.keys.contains(key))
        self.lock.lock()
        defer { self.lock.unlock() }
        if self.snapshot == nil {
            let defaults = UserDefaults.standard
            var values: [String: Any] = [:]
            for key in self.keys {
                if let value = defaults.object(forKey: key) {
                    values[key] = value
                }
            }
            self.snapshot = values
        }
        return self.snapshot?[key]
    }
}

'''


def patch_reads(text):
    def replace(match):
        kind, key = match.groups()
        if key not in KEYS:
            return match.group(0)
        call = 'JerkgramHotSettings.object(forKey: "' + key + '")'
        return '(' + call + ' as? String)' if kind == "string" else call
    return READ.sub(replace, text)


def refresh_at_exit(text, signature):
    block = base.function_block(text, signature)
    if "defer { JerkgramHotSettings.invalidate() }" not in block:
        updated = block.replace("{", "{\n    defer { JerkgramHotSettings.invalidate() }", 1)
        return text.replace(block, updated, 1)
    return text


def patch_settings(text):
    signature = "private func jerkgramPersistChangedSettings("
    block = base.function_block(text, signature)
    pattern = r"(let jerkgramSynchronousRuntimeSettingKeys: Set<String> = \[[\s\S]*?\])(?!\.union)"
    if "].union(JerkgramHotSettings.keys)" not in block:
        block, count = re.subn(pattern, r"\1.union(JerkgramHotSettings.keys)", block, count=1)
        base.require(count == 1, "settings synchronous key set missing")
        text = base.replace_function(text, signature, block)
    return refresh_at_exit(text, signature)


def strip_diagnostics(text):
    # Only complete, standalone calls with explicitly retired diagnostic keys.
    starts = list(re.finditer(r"(?m)^[ \t]*UserDefaults\.standard\.set\(", text))
    for match in reversed(starts):
        opening = text.index("(", match.start())
        depth, quoted, escaped = 0, False, False
        end = None
        for i in range(opening, len(text)):
            ch = text[i]
            if quoted:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    quoted = False
            elif ch == '"':
                quoted = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        base.require(end is not None, "diagnostic call unbalanced")
        call = text[match.start():end]
        if re.search(r'"jerkgram\.(?:READ3\.|V10T\.SendTextStyleApplied\.Count|V10S\.InlineScheduledIntercept\.Count)', call):
            text = text[:match.start()] + text[end:]
    text = re.sub(r"if let first = items\.first \{\s*\}", "", text)
    text = re.sub(r"if items\.isEmpty \{\s*\} else \{\s*\}", "", text)
    return text


def patch_source_probe(text):
    return base.replace_function(text, "private func ghostBaseV10NSaveSourcePeerId(",
        '''private func ghostBaseV10NSaveSourcePeerId(_ peerId: PeerId, source: String) {
    // Retired source-peer diagnostics; no persistence on chat entry.
}''')


def patch_activity_lock(text):
    signature = "private static func settings() -> JerkgramActivityGhostSettings"
    block = base.function_block(text, signature)
    if "return self.cached.modify" in block:
        return text
    start = block.index("        let defaults = UserDefaults.standard")
    end = block.index("        let _ = self.cached.modify")
    load = block[start:end]
    replacement = signature + ''' {
        // Load and publish under the same lock used by invalidate().
        return self.cached.modify { cached in
            if let cached = cached { return cached }
''' + "\n".join("    " + line for line in load.rstrip().splitlines()) + '''
            return loaded
        }!
    }'''
    return base.replace_function(text, signature, replacement)


def patch_blocked_lock(text):
    signature = "private static func settings(accountPeerId: PeerId) -> JerkgramBuild137BlockedSettings"
    block = base.function_block(text, signature)
    if "let result = self.settingsByAccount.modify" in block:
        return text
    start = block.index("        let defaults = UserDefaults.standard")
    end = block.index("        let _ = self.settingsByAccount.modify")
    load = block[start:end]
    replacement = signature + ''' {
        let result = self.settingsByAccount.modify { current in
            if current[accountPeerId] != nil { return current }
''' + "\n".join("    " + line for line in load.rstrip().splitlines()) + '''
            var current = current
            current[accountPeerId] = loaded
            return current
        }
        // Every closure path returns a dictionary containing this account.
        return result[accountPeerId]!
    }'''
    return base.replace_function(text, signature, replacement)


def restore_history_invalidation(text):
    if "let mustRefreshFallback" in text:
        return text
    anchor = "if let cached = cachedEntries[key],"
    base.require(text.count(anchor) == 1, "fallback reuse owner missing")
    refresh = '''let mustRefreshFallback: Bool
        if item.messages.isEmpty {
            switch update.type {
            case .Generic, .FillHole:
                mustRefreshFallback = true
            default:
                mustRefreshFallback = false
            }
        } else {
            mustRefreshFallback = false
        }
        '''
    text = text.replace(anchor, refresh + anchor, 1)
    pattern = r"(cached.presentationRevision == presentationRevision)\s*\{"
    text, count = re.subn(pattern, r"\1,\n           !mustRefreshFallback {", text, count=1)
    base.require(count == 1, "fallback revision comparison missing")
    return text


def patch_glass_refresh(text):
    if "public static func reloadFromDefaults()" not in text:
        anchor = "    public static var isEnabled: Bool"
        base.require(text.count(anchor) == 1, "Glass getter missing")
        text = text.replace(anchor, '''    public static func reloadFromDefaults() {
        self.enabledLock.lock()
        defer { self.enabledLock.unlock() }
        self.enabledValue = UserDefaults.standard.object(forKey: self.enabledKey) as? Bool ?? true
    }

''' + anchor, 1)
    return base.replace_function(text, "public static func setEnabled(_ value: Bool)", '''public static func setEnabled(_ value: Bool) {
        self.enabledLock.lock()
        self.enabledValue = value
        self.enabledLock.unlock()
        UserDefaults.standard.set(value, forKey: self.enabledKey)
    }''')


def refresh_projection(text, signature):
    block = base.function_block(text, signature)
    if "GhostBaseGlassStyle.reloadFromDefaults()" in block:
        return text
    text = refresh_at_exit(text, signature)
    block = base.function_block(text, signature)
    old = "defer { JerkgramHotSettings.invalidate() }"
    new = '''defer {
        JerkgramHotSettings.invalidate()
        JerkgramActivityGhostRuntime.invalidate()
        JerkgramBlockedReactionPolicy.notifySettingsChanged()
        GhostBaseGlassStyle.reloadFromDefaults()
        Queue.mainQueue().async {
            NotificationCenter.default.post(name: Notification.Name("''' + base.RAM_NOTIFICATION + '''"), object: nil)
        }
    }'''
    # The defer also covers every early return; remove the older duplicate call.
    block = block.replace("    JerkgramActivityGhostRuntime.invalidate()\n", "")
    return base.replace_function(text, signature, block.replace(old, new, 1))


def patch_ram_theme(text):
    anchor = "                if previousTheme !== presentationData.theme {"
    line = "                    strongSelf.ghostBaseRamLabel?.textColor = presentationData.theme.overallDarkAppearance ? UIColor.white.withAlphaComponent(0.78) : UIColor.black.withAlphaComponent(0.68)"
    if line in text:
        return text
    base.require(text.count(anchor) == 1, "RAM theme update anchor missing")
    return text.replace(anchor, anchor + "\n" + line, 1)


def main():
    changes = {}
    def put(path, transform):
        source = changes.get(path, path.read_text())
        changes[path] = transform(source)
    # Validate all transformations before any source is written.
    for module in MODULES:
        for path in (ROOT / "submodules" / module).rglob("*.swift"):
            source = path.read_text()
            updated = patch_reads(source)
            if updated != source:
                base.require(module == "TelegramCore" or "import TelegramCore" in source,
                             "missing TelegramCore import: " + str(path))
                changes[path] = updated
    def install(source):
        if MARKER in source:
            return source
        anchor = "public final class Account"
        base.require(anchor in source, "Account owner missing")
        return source.replace(anchor, RUNTIME + anchor, 1)
    put(base.ACCOUNT, install)
    put(base.SETTINGS, patch_settings)
    put(base.ACCOUNT, patch_activity_lock)
    put(base.BLOCKED_POLICY, patch_blocked_lock)
    put(base.CHAT_LIST, restore_history_invalidation)
    put(base.GLASS, patch_glass_refresh)
    put(base.RAM_ROOT, patch_ram_theme)
    put(base.SHARED_ACCOUNT_CONTEXT, lambda s: refresh_projection(s, "private func jerkgramBuild135ProjectAccountSettings("))
    put(ARCHIVE, lambda s: refresh_projection(s, "private func jerkgramProjectImportedSettingsToActiveDefaults("))
    put(CHAT_LOAD, patch_source_probe)
    put(CHAT_CONTROLLER, strip_diagnostics)
    put(READ_STATS, strip_diagnostics)
    count = 0
    for path, updated in changes.items():
        if path.read_text() != updated:
            path.write_text(updated)
            count += 1
    print("[Build137 performance2] materialized; changed owners:", count)


if __name__ == "__main__":
    main()
