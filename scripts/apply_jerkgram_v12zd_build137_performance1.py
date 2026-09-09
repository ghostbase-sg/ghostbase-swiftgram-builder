#!/usr/bin/env python3

from pathlib import Path
import os
import re


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
APP_DELEGATE = ROOT / "submodules/TelegramUI/Sources/AppDelegate.swift"
RAM_ROOT = ROOT / "submodules/TelegramUI/Sources/TelegramRootController.swift"
SETTINGS = ROOT / "submodules/SettingsUI/Sources/GhostBase/GhostBaseSettingsController.swift"
GLASS = ROOT / "submodules/Display/Source/GhostBaseGlass.swift"
BLOCKED_POLICY = ROOT / "submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeersContext.swift"
CHAT_LIST = ROOT / "submodules/ChatListUI/Sources/Node/ChatListNodeLocation.swift"
STATE = ROOT / "submodules/TelegramCore/Sources/State/AccountStateManagementUtils.swift"
CONSUME = ROOT / "submodules/TelegramCore/Sources/TelegramEngine/Messages/MarkMessageContentAsConsumedInteractively.swift"
ACCOUNT = ROOT / "submodules/TelegramCore/Sources/Account/Account.swift"
MANAGED_ACTIVITY = ROOT / "submodules/TelegramCore/Sources/State/ManagedLocalInputActivities.swift"
SHARED_ACCOUNT_CONTEXT = ROOT / "submodules/TelegramUI/Sources/SharedAccountContext.swift"
UPDATE_PEERS = ROOT / "submodules/TelegramCore/Sources/UpdatePeers.swift"

MARKER = "// MARK: Jerkgram v1.2ZD BUILD137_PERFORMANCE1"
MEMORY_SAMPLER_MARKER = "// MARK: Jerkgram v1.2ZD BUILD137_MEMORY_SAMPLER1"
RAM_NOTIFICATION = "GhostBaseRamOverlayPreferenceChanged"
APP_LAUNCH_SIGNATURE = "func application(_ application: UIApplication, didFinishLaunchingWithOptions"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build137 performance] " + message)


def function_bounds(text: str, signature: str) -> tuple[int, int]:
    start = text.find(signature)
    require(start >= 0, "missing function/property owner: " + signature)
    opening = text.find("{", start)
    require(opening >= 0, "missing opening brace: " + signature)
    depth = 0
    in_string = False
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1
    raise RuntimeError("[Build137 performance] unbalanced owner: " + signature)


def function_block(text: str, signature: str) -> str:
    start, end = function_bounds(text, signature)
    return text[start:end]


def property_block(text: str, signature: str) -> str:
    return function_block(text, signature)


def replace_function(text: str, signature: str, replacement: str) -> str:
    start, end = function_bounds(text, signature)
    return text[:start] + replacement + text[end:]


RAM_ROOT_FIXTURE = r'''public final class TelegramRootController {
    // MARK: GhostBase v1.1R RAM_OVERLAY1
    private var ghostBaseRamLabel: UILabel?
    private var ghostBaseRamTimer: Foundation.Timer?
    private var ghostBaseRamDefaultsObserver: NSObjectProtocol?
    private var ghostBaseRamActiveObserver: NSObjectProtocol?
    private var ghostBaseRamInactiveObserver: NSObjectProtocol?
    private var ghostBaseRamLayout: ContainerViewLayout?

    private static let ghostBaseRamEnabledKey =
        "GhostBase.Appearance.ShowRamUnderClock"

    private func ghostBaseSetupRamOverlay() {
        self.ghostBaseRamDefaultsObserver = NotificationCenter.default.addObserver(
            forName: UserDefaults.didChangeNotification,
            object: UserDefaults.standard,
            queue: .main,
            using: { [weak self] _ in
                self?.ghostBaseUpdateRamOverlayState()
            }
        )
        self.ghostBaseRamActiveObserver = NotificationCenter.default.addObserver(
            forName: UIApplication.didBecomeActiveNotification,
            object: nil,
            queue: .main,
            using: { [weak self] _ in self?.ghostBaseUpdateRamOverlayState() }
        )
        self.ghostBaseRamInactiveObserver = NotificationCenter.default.addObserver(
            forName: UIApplication.willResignActiveNotification,
            object: nil,
            queue: .main,
            using: { [weak self] _ in self?.ghostBaseUpdateRamOverlayState(forceInactive: true) }
        )
        self.ghostBaseUpdateRamOverlayState()
    }

    private func ghostBaseUpdateRamOverlayState(forceInactive: Bool = false) {
        let enabled = (UserDefaults.standard.object(forKey: Self.ghostBaseRamEnabledKey) as? Bool) ?? false
        let active = !forceInactive && UIApplication.shared.applicationState == .active
        guard enabled && active else { return }
        let label = UILabel()
        self.ghostBaseRamLabel = label
        if self.ghostBaseRamTimer == nil {
            let timer = Foundation.Timer(timeInterval: 1.0, repeats: true) { [weak self] _ in
                self?.ghostBaseUpdateRamValue()
            }
            RunLoop.main.add(timer, forMode: .common)
            self.ghostBaseRamTimer = timer
        }
        self.ghostBaseUpdateRamValue()
        self.ghostBaseLayoutRamLabel()
        self.view.bringSubviewToFront(label)
    }

    private func ghostBaseCurrentMemoryFootprint() -> UInt64? {
        return 1024
    }

    private func ghostBaseUpdateRamValue() {
        guard let label = self.ghostBaseRamLabel else { return }
        if let bytes = self.ghostBaseCurrentMemoryFootprint() {
            label.text = "RAM \(bytes) MB"
        } else {
            label.text = "RAM —"
        }
    }

    private func ghostBaseLayoutRamLabel() {}

    override public func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        self.ghostBaseRamLayout = layout
        self.ghostBaseUpdateRamOverlayState()
        self.ghostBaseLayoutRamLabel()
    }
}
'''


APP_DELEGATE_FIXTURE = r'''private func getMemoryConsumption() -> Int {
    return 1024
}

@objc(AppDelegate) class AppDelegate: UIResponder {
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        var previousReportedMemoryConsumption = 0
        let _ = Foundation.Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true, block: { _ in
            let value = getMemoryConsumption()
            if abs(value - previousReportedMemoryConsumption) > 1 * 1024 * 1024 {
                previousReportedMemoryConsumption = value
                Logger.shared.log("App", "Memory consumption: \(value)")
            }
        })
        return true
    }
}
'''


SETTINGS_FIXTURE = r'''private enum GhostBaseKey {
    static let glassEnabled = "GhostBase.Glass.Enabled"
    static let showRamUnderClock = "GhostBase.Appearance.ShowRamUnderClock"
}

func updateSetting(key: String, value: Bool) {
    switch key {
    case GhostBaseKey.glassEnabled:
        updated.glassEnabled = value
        UserDefaults.standard.set(value, forKey: GhostBaseKey.glassEnabled)

    case GhostBaseKey.showRamUnderClock:
        updated.showRamUnderClock = value
        UserDefaults.standard.set(
            value,
            forKey: GhostBaseKey.showRamUnderClock
        )
    default:
        break
    }
}
'''


GLASS_FIXTURE = r'''public enum GhostBaseGlassStyle {
    public static let enabledKey = "GhostBase.Glass.Enabled"

    public static var isEnabled: Bool {
        if let value = UserDefaults.standard.object(forKey: self.enabledKey) as? Bool {
            return value
        }
        return true
    }

    public static func setEnabled(_ value: Bool) {
        UserDefaults.standard.set(value, forKey: self.enabledKey)
    }
}
'''


BLOCKED_POLICY_FIXTURE = r'''public enum JerkgramBlockedReactionPolicy {
    public static let hideBlockedReactionsKey = "jerkgram.Messages.HideBlockedReactions"
    public static let hideBlockedMessagesKey = "jerkgram.Messages.HideBlockedMessages"
    private static let blockedPeerIdsByAccount = Atomic(value: [PeerId: Set<PeerId>]())

    public static func notifySettingsChanged() {
        self.notifyPresentationChanged()
    }

    public static func hideBlockedReactions(accountPeerId: PeerId) -> Bool {
        let defaults = UserDefaults.standard
        let scopedKey = "jerkgram.account.\(accountPeerId.toInt64()).setting.\(self.hideBlockedReactionsKey)"
        if let value = defaults.object(forKey: scopedKey) as? Bool { return value }
        if let value = defaults.object(forKey: self.hideBlockedReactionsKey) as? Bool { return value }
        return true
    }

    public static func hideBlockedMessages(accountPeerId: PeerId) -> Bool {
        let defaults = UserDefaults.standard
        let scopedKey = "jerkgram.account.\(accountPeerId.toInt64()).setting.\(self.hideBlockedMessagesKey)"
        if let value = defaults.object(forKey: scopedKey) as? Bool { return value }
        if let value = defaults.object(forKey: self.hideBlockedMessagesKey) as? Bool { return value }
        return true
    }
}
'''


CHAT_LIST_FIXTURE = r'''if let cached = cachedEntries[key],
   cached.sourceIndex == item.index,
   cached.stockUnreadCount == stockUnreadCount,
   cached.presentationRevision == presentationRevision,
   !mustRefreshFallback {
    reusable[peerId] = cached
} else {
    missingPeerIds.insert(peerId)
}
let mustRefreshFallback: Bool
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


DIAGNOSTICS_FIXTURE = r'''private enum GhostBaseRuntimeDiagnosticsV11G {
    private static let queue = DispatchQueue(label: "diagnostics")
    static func record(_ event: String) {
        self.queue.async {
            let defaults = UserDefaults.standard
            defaults.set(event, forKey: "jerkgram.Runtime.Diagnostics.V11G")
        }
    }
}
'''


ONETIME_FIXTURE = r'''if ghostBaseOT1KeepOutgoingTimerLocal {
    UserDefaults.standard.set(UserDefaults.standard.integer(forKey: "jerkgram.OT1.OutgoingKeepBlocked.Count") + 1, forKey: "jerkgram.OT1.OutgoingKeepBlocked.Count")
    UserDefaults.standard.set("consumeImage", forKey: "jerkgram.OT1.OutgoingKeepPath")
    return .single(true)
}
'''


ACCOUNT_ACTIVITY_FIXTURE = r'''public final class Account {
    public func updateLocalInputActivity(peerId: PeerActivitySpace, activity: PeerInputActivity, isPresent: Bool) {
        // MARK: GhostBase v0.5B Activity Ghost runtime
        if isPresent {
            let ghostBaseHideTyping = (UserDefaults.standard.object(forKey: "jerkgram.GhostMode.TypingActions") as? Bool) ?? false
            let ghostBaseHideRecording = (UserDefaults.standard.object(forKey: "jerkgram.GhostMode.HideRecording") as? Bool) ?? false
            let ghostBaseHideUploading = (UserDefaults.standard.object(forKey: "jerkgram.GhostMode.HideUploading") as? Bool) ?? false
            let ghostBaseHideStickerActivity = (UserDefaults.standard.object(forKey: "jerkgram.GhostMode.HideStickerActivity") as? Bool) ?? false
            let ghostBaseHideGameActivity = (UserDefaults.standard.object(forKey: "jerkgram.GhostMode.HideGameActivity") as? Bool) ?? false
            let ghostBaseHideEmojiActivity = (UserDefaults.standard.object(forKey: "jerkgram.GhostMode.HideEmojiActivity") as? Bool) ?? false
            if ghostBaseHideTyping { return }
        }
        self.localInputActivityManager.transaction { manager in
            if isPresent {
                manager.addActivity(chatPeerId: peerId, peerId: self.peerId, activity: activity)
            } else {
                manager.removeActivity(chatPeerId: peerId, peerId: self.peerId, activity: activity)
            }
        }
    }
}
'''


MANAGED_ACTIVITY_FIXTURE = r'''private func requestActivity(postbox: Postbox, network: Network, accountPeerId: PeerId, peerId: PeerId, threadId: Int64?, activity: PeerInputActivity?) -> Signal<Void, NoError> {
    // MARK: GhostBase v0.5C Activity Ghost lower-layer guard
    if let activity = activity {
        let ghostBaseHideTyping = (UserDefaults.standard.object(forKey: "jerkgram.GhostMode.TypingActions") as? Bool) ?? false
        let ghostBaseHideRecording = (UserDefaults.standard.object(forKey: "jerkgram.GhostMode.HideRecording") as? Bool) ?? false
        let ghostBaseSuppressActivity = ghostBaseHideTyping || ghostBaseHideRecording
        if ghostBaseSuppressActivity { return .complete() }
    }
    return postbox.transaction { _ in }
}
'''


UPDATE_PEERS_FIXTURE = r'''// MARK: GhostBase v1.1B PRESENCEGLOBAL2 transition archive
private func ghostBasePresenceTransitionKey(_ event: GhostBasePresenceHistoryEvent) -> String {
    return "\(event.status)|hidden=\(event.isHidden)"
}

private func ghostBaseRecordPresence(accountPeerId: PeerId, peerId: PeerId, presence: TelegramUserPresence) {
    guard let event = ghostBasePresenceEvent(presence) else { return }
    let key = ghostBasePresenceHistoryKey(accountPeerId: accountPeerId, peerId: peerId)
    var events: [GhostBasePresenceHistoryEvent] = []
    if let data = UserDefaults.standard.data(forKey: key), let value = try? JSONDecoder().decode([GhostBasePresenceHistoryEvent].self, from: data) {
        events = ghostBaseCompactPresenceEvents(value)
    }
    if let previous = events.last, ghostBasePresenceTransitionKey(previous) == ghostBasePresenceTransitionKey(event) {
        if let data = try? JSONEncoder().encode(events) { UserDefaults.standard.set(data, forKey: key) }
        return
    }
}

private func ghostBaseRegisterKnownUser(accountPeerId: PeerId, user: TelegramUser) {
    let key = ghostBaseKnownUserKey(accountPeerId: accountPeerId, peerId: user.id)
    let now = Int64(Date().timeIntervalSince1970)
    let decoder = JSONDecoder()
    let encoder = JSONEncoder()
    let previous: GhostBaseKnownUser?
    if let data = UserDefaults.standard.data(forKey: key) {
        previous = try? decoder.decode(GhostBaseKnownUser.self, from: data)
    } else {
        previous = nil
    }
    let record = GhostBaseKnownUser(peerId: user.id.toInt64(), title: user.nameOrPhone, username: user.addressName, isBot: user.botInfo != nil, firstSeen: previous?.firstSeen ?? now, lastSeen: now)
    if let data = try? encoder.encode(record) { UserDefaults.standard.set(data, forKey: key) }
}
'''


MEMORY_SAMPLER = r'''// MARK: Jerkgram v1.2ZD BUILD137_MEMORY_SAMPLER1
final class JerkgramMemorySampler {
    static let shared = JerkgramMemorySampler()

    private let queue = DispatchQueue(label: "jerkgram.memory.sampler", qos: .utility)
    private let lock = NSLock()
    private var isSampling = false
    private var completions: [String: (Int) -> Void] = [:]

    func sample(consumer: String, _ completion: @escaping (Int) -> Void) {
        self.lock.lock()
        self.completions[consumer] = completion
        if self.isSampling {
            self.lock.unlock()
            return
        }
        self.isSampling = true
        self.lock.unlock()

        self.queue.async { [weak self] in
            let value = getMemoryConsumption()
            guard let self else { return }
            self.lock.lock()
            let completions = Array(self.completions.values)
            self.completions.removeAll(keepingCapacity: true)
            self.isSampling = false
            self.lock.unlock()
            Queue.mainQueue().async {
                for completion in completions {
                    completion(value)
                }
            }
        }
    }
}
'''


def patch_app_delegate_memory(text: str) -> str:
    while MEMORY_SAMPLER_MARKER + "\n" + MEMORY_SAMPLER_MARKER in text:
        text = text.replace(MEMORY_SAMPLER_MARKER + "\n" + MEMORY_SAMPLER_MARKER, MEMORY_SAMPLER_MARKER, 1)

    app_delegate_match = re.search(
        r"(?m)^(?:@objc\(AppDelegate\)\s+)?(?:final\s+)?class AppDelegate\b",
        text,
    )
    require(app_delegate_match is not None, "AppDelegate type owner missing")
    app_delegate = app_delegate_match.start()
    sampler = text.find(MEMORY_SAMPLER_MARKER)
    if sampler >= 0:
        require(sampler < app_delegate, "memory sampler marker is outside AppDelegate prefix")
        text = text[:sampler] + MEMORY_SAMPLER + "\n" + text[app_delegate:]
    else:
        text = text[:app_delegate] + MEMORY_SAMPLER + "\n" + text[app_delegate:]

    launch_signature = APP_LAUNCH_SIGNATURE
    launch = function_block(text, launch_signature)
    old_header = (
        "        var previousReportedMemoryConsumption = 0\n"
        "        let _ = Foundation.Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true, block: { _ in\n"
        "            let value = getMemoryConsumption()\n"
    )
    if old_header in launch:
        new_header = (
            "        var previousReportedMemoryConsumption = 0\n"
            "        let jerkgramMemoryTimer = Foundation.Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true, block: { _ in\n"
            "            JerkgramMemorySampler.shared.sample(consumer: \"appDelegate\") { value in\n"
        )
        launch = launch.replace(old_header, new_header, 1)
        timer_end = launch.find("\n        })", launch.find(new_header) + len(new_header))
        require(timer_end >= 0, "stock memory timer closing owner missing")
        launch = (
            launch[:timer_end]
            + "\n            }"
            + launch[timer_end:timer_end + len("\n        })")]
            + "\n        jerkgramMemoryTimer.tolerance = 0.25"
            + launch[timer_end + len("\n        })"):]
        )
        text = replace_function(text, launch_signature, launch)
    else:
        require('sample(consumer: "appDelegate")' in launch, "stock memory timer owner missing")
        if "jerkgramMemoryTimer.tolerance = 0.25" not in launch:
            timer_end = launch.find("\n        })", launch.find('sample(consumer: "appDelegate")'))
            require(timer_end >= 0, "patched memory timer closing owner missing")
            insert = timer_end + len("\n        })")
            launch = launch[:insert] + "\n        jerkgramMemoryTimer.tolerance = 0.25" + launch[insert:]
            text = replace_function(text, launch_signature, launch)
    return text


def patch_ram_root(text: str) -> str:
    require("GhostBase v1.1R RAM_OVERLAY1" in text, "RAM overlay baseline missing")
    if MARKER not in text:
        text = text.replace(
            "    private var ghostBaseRamLayout: ContainerViewLayout?\n",
            "    private var ghostBaseRamLayout: ContainerViewLayout?\n"
            "    " + MARKER + "\n",
            1,
        )
    text = text.replace(
        "    private static let ghostBaseRamMeasurementQueue = DispatchQueue(label: \"jerkgram.ram.measurement\", qos: .utility)\n",
        "",
    )
    text = text.replace("    private var ghostBaseRamMeasurementInFlight = false\n", "")
    setup = function_block(text, "private func ghostBaseSetupRamOverlay()")
    setup = setup.replace("forName: UserDefaults.didChangeNotification", f'forName: Notification.Name("{RAM_NOTIFICATION}")')
    setup = setup.replace("object: UserDefaults.standard", "object: nil")
    text = replace_function(text, "private func ghostBaseSetupRamOverlay()", setup)

    timer_pattern = re.compile(r"(?m)^(?P<i>\s*)let timer = Foundation\.Timer\(timeInterval: 1\.0, repeats: true\) \{ \[weak self\] _ in\n(?P=i)    self\?\.ghostBaseUpdateRamValue\(\)\n(?P=i)\}(?!\n(?P=i)timer\.tolerance = 0\.5)")
    match = timer_pattern.search(text)
    if match is not None:
        timer = match.group(0) + "\n" + match.group("i") + "timer.tolerance = 0.5"
        text = text[:match.start()] + timer + text[match.end():]
    require("timer.tolerance = 0.5" in text, "RAM timer owner missing")

    if "private func ghostBaseCurrentMemoryFootprint()" in text:
        start, end = function_bounds(text, "private func ghostBaseCurrentMemoryFootprint()")
        while end < len(text) and text[end] == "\n":
            end += 1
        text = text[:start] + text[end:]

    update = r'''private func ghostBaseUpdateRamValue() {
        guard self.ghostBaseRamLabel != nil else { return }
        JerkgramMemorySampler.shared.sample(consumer: "ramOverlay") { [weak self] bytes in
            guard let label = self?.ghostBaseRamLabel else { return }
            if bytes > 0 {
                let megabytes = Int((bytes + 524_288) / 1_048_576)
                label.text = "RAM \(megabytes) MB"
            } else {
                label.text = "RAM —"
            }
        }
    }'''
    text = replace_function(text, "private func ghostBaseUpdateRamValue()", update)

    layout = function_block(text, "override public func containerLayoutUpdated(")
    layout = layout.replace("        self.ghostBaseUpdateRamOverlayState()\n", "")
    text = replace_function(text, "override public func containerLayoutUpdated(", layout)
    return text


def patch_settings(text: str) -> str:
    text = text.replace(
        "UserDefaults.standard.set(value, forKey: GhostBaseKey.glassEnabled)",
        "GhostBaseGlassStyle.setEnabled(value)",
    )
    ram_case = functionless_case_block(text, "case GhostBaseKey.showRamUnderClock:")
    if RAM_NOTIFICATION not in ram_case:
        compact = "UserDefaults.standard.set(value, forKey: GhostBaseKey.showRamUnderClock)"
        notification = f'\n        NotificationCenter.default.post(name: Notification.Name("{RAM_NOTIFICATION}"), object: nil)'
        multiline = re.compile(
            r"UserDefaults\.standard\.set\(\s*value,\s*"
            r"forKey: GhostBaseKey\.showRamUnderClock\s*\)",
            flags=re.MULTILINE,
        )
        match = multiline.search(ram_case)
        if match is not None:
            ram_case = ram_case[:match.end()] + notification + ram_case[match.end():]
        elif compact in ram_case:
            ram_case = ram_case.replace(compact, compact + notification, 1)
        else:
            raise RuntimeError("[Build137 performance] RAM setting persistence owner missing")
        text = replace_case_block(text, "case GhostBaseKey.showRamUnderClock:", ram_case)

    if "private func jerkgramPersistChangedSettings(" not in text:
        return text
    sync_start = text.find("let jerkgramSynchronousRuntimeSettingKeys: Set<String> = [")
    require(sync_start >= 0, "synchronous Settings runtime key owner missing")
    sync_end = text.find("    ]", sync_start)
    require(sync_end > sync_start, "synchronous Settings runtime key boundary missing")
    sync_block = text[sync_start:sync_end]
    activity_keys = (
        "typingActions",
        "recordingActions",
        "uploadingActions",
        "stickerActivity",
        "gameActivity",
        "emojiActivity",
    )
    missing = [name for name in activity_keys if f"GhostBaseKey.{name}" not in sync_block]
    if missing:
        insertion = "".join(f"        GhostBaseKey.{name},\n" for name in missing)
        text = text[:sync_end] + insertion + text[sync_end:]
    persist = function_block(text, "private func jerkgramPersistChangedSettings(")
    if "JerkgramActivityGhostRuntime.invalidate()" not in persist:
        loop_start = persist.find("for key in jerkgramSynchronousRuntimeSettingKeys {")
        require(loop_start >= 0, "synchronous Settings write loop missing")
        _, loop_end = function_bounds(text, "for key in jerkgramSynchronousRuntimeSettingKeys {")
        text = text[:loop_end] + "\n    JerkgramActivityGhostRuntime.invalidate()" + text[loop_end:]
    return text


def functionless_case_bounds(text: str, signature: str) -> tuple[int, int]:
    start = text.find(signature)
    require(start >= 0, "missing switch case: " + signature)
    match = re.search(r"(?m)^\s*(?:case |default:)", text[start + len(signature):])
    end = len(text) if match is None else start + len(signature) + match.start()
    return start, end


def functionless_case_block(text: str, signature: str) -> str:
    start, end = functionless_case_bounds(text, signature)
    return text[start:end]


def replace_case_block(text: str, signature: str, replacement: str) -> str:
    start, end = functionless_case_bounds(text, signature)
    return text[:start] + replacement + text[end:]


def patch_glass_runtime(text: str) -> str:
    if "private static let enabledLock" in text:
        return text
    old_getter = property_block(text, "public static var isEnabled: Bool")
    new_getter = '''private static let enabledLock = NSLock()
    private static var enabledValue: Bool = {
        return UserDefaults.standard.object(forKey: enabledKey) as? Bool ?? true
    }()

    public static var isEnabled: Bool {
        self.enabledLock.lock()
        defer { self.enabledLock.unlock() }
        return self.enabledValue
    }'''
    text = text.replace(old_getter, new_getter, 1)
    setter = '''public static func setEnabled(_ value: Bool) {
        self.enabledLock.lock()
        self.enabledValue = value
        self.enabledLock.unlock()
        UserDefaults.standard.set(value, forKey: self.enabledKey)
    }'''
    text = replace_function(text, "public static func setEnabled(_ value: Bool)", setter)
    return text


def patch_blocked_policy(text: str) -> str:
    if "JerkgramBuild137BlockedSettings" not in text:
        anchor = "    private static let blockedPeerIdsByAccount = Atomic(value: [PeerId: Set<PeerId>]())\n"
        require(anchor in text, "blocked policy cache anchor missing")
        helper = r'''
    private struct JerkgramBuild137BlockedSettings {
        let hideReactions: Bool
        let hideMessages: Bool
    }
    private static let settingsByAccount = Atomic(value: [PeerId: JerkgramBuild137BlockedSettings]())

    private static func settings(accountPeerId: PeerId) -> JerkgramBuild137BlockedSettings {
        if let cached = self.settingsByAccount.with({ $0[accountPeerId] }) {
            return cached
        }
        let defaults = UserDefaults.standard
        func value(_ key: String) -> Bool {
            let scopedKey = "jerkgram.account.\(accountPeerId.toInt64()).setting.\(key)"
            if let value = defaults.object(forKey: scopedKey) as? Bool { return value }
            if let value = defaults.object(forKey: key) as? Bool { return value }
            return true
        }
        let loaded = JerkgramBuild137BlockedSettings(
            hideReactions: value(self.hideBlockedReactionsKey),
            hideMessages: value(self.hideBlockedMessagesKey)
        )
        let _ = self.settingsByAccount.modify { current in
            var current = current
            current[accountPeerId] = loaded
            return current
        }
        return loaded
    }
'''
        text = text.replace(anchor, anchor + helper, 1)
    notify = function_block(text, "public static func notifySettingsChanged()")
    if "settingsByAccount" not in notify:
        notify = notify.replace(
            "{",
            "{\n        let _ = self.settingsByAccount.modify { _ in [:] }",
            1,
        )
        text = replace_function(text, "public static func notifySettingsChanged()", notify)
    for signature, field in (
        ("public static func hideBlockedReactions(", "hideReactions"),
        ("public static func hideBlockedMessages(", "hideMessages"),
    ):
        block = function_block(text, signature)
        header = block[:block.find("{") + 1]
        replacement = header + f"\n        return self.settings(accountPeerId: accountPeerId).{field}\n    }}"
        text = text.replace(block, replacement, 1)
    return text


def patch_chat_list_helper(text: str) -> str:
    pattern = re.compile(
        r"\s*let mustRefreshFallback: Bool\n"
        r"\s*if item\.messages\.isEmpty \{\n"
        r"\s*switch update\.type \{\n"
        r"\s*case \.Generic, \.FillHole:\n"
        r"\s*mustRefreshFallback = true\n"
        r"\s*default:\n"
        r"\s*mustRefreshFallback = false\n"
        r"\s*\}\n"
        r"\s*\} else \{\n"
        r"\s*mustRefreshFallback = false\n"
        r"\s*\}\n"
    )
    text, count = pattern.subn("\n", text, count=1)
    require(count == 1 or "mustRefreshFallback" not in text, "forced fallback refresh owner missing")
    text = re.sub(r",\n\s*!mustRefreshFallback\s*\{", " {", text, count=1)
    return text


def patch_runtime_diagnostics(text: str) -> str:
    if "GhostBaseRuntimeDiagnosticsV11G" not in text:
        return text
    block = function_block(text, "static func record(_ event: String)")
    replacement = '''static func record(_ event: String) {
        // Release builds keep no persistent probe log on the update path.
        _ = event
    }'''
    return text.replace(block, replacement, 1)


def strip_legacy_diagnostic_writes(text: str) -> str:
    diagnostic = re.compile(r"(?:GhostBase|jerkgram)\.(?:OT1|OT2|SH1|SH2|V10[A-Q]|READ3)\.")
    result = []
    for line in text.splitlines(keepends=True):
        if "UserDefaults.standard.set" in line and diagnostic.search(line):
            continue
        result.append(line)
    return "".join(result)


ACTIVITY_RUNTIME = r'''// MARK: Jerkgram v1.2ZD BUILD137_ACTIVITY_SNAPSHOT1
private struct JerkgramActivityGhostSettings {
    let typing: Bool
    let recording: Bool
    let uploading: Bool
    let sticker: Bool
    let game: Bool
    let emoji: Bool
}

public enum JerkgramActivityGhostRuntime {
    private static let cached = Atomic(value: JerkgramActivityGhostSettings?.none)

    public static func invalidate() {
        let _ = self.cached.modify { _ in nil }
    }

    private static func settings() -> JerkgramActivityGhostSettings {
        if let cached = self.cached.with({ $0 }) {
            return cached
        }
        let defaults = UserDefaults.standard
        func value(_ key: String) -> Bool {
            return defaults.object(forKey: key) as? Bool ?? false
        }
        let loaded = JerkgramActivityGhostSettings(
            typing: value("jerkgram.GhostMode.TypingActions"),
            recording: value("jerkgram.GhostMode.HideRecording"),
            uploading: value("jerkgram.GhostMode.HideUploading"),
            sticker: value("jerkgram.GhostMode.HideStickerActivity"),
            game: value("jerkgram.GhostMode.HideGameActivity"),
            emoji: value("jerkgram.GhostMode.HideEmojiActivity")
        )
        let _ = self.cached.modify { _ in loaded }
        return loaded
    }

    public static func shouldSuppress(_ activity: PeerInputActivity) -> Bool {
        let settings = self.settings()
        switch activity {
        case .typingText:
            return settings.typing
        case .recordingVoice, .recordingInstantVideo:
            return settings.recording
        case .uploadingFile(_), .uploadingPhoto(_), .uploadingVideo(_), .uploadingInstantVideo(_):
            return settings.uploading
        case .choosingSticker:
            return settings.sticker
        case .playingGame:
            return settings.game
        case .interactingWithEmoji(_, _, _), .seeingEmojiInteraction(_):
            return settings.emoji
        default:
            return false
        }
    }
}

'''


def patch_account_activity(text: str) -> str:
    if "BUILD137_ACTIVITY_SNAPSHOT1" not in text:
        class_anchor = "public final class Account"
        index = text.find(class_anchor)
        require(index >= 0, "Account type owner missing")
        text = text[:index] + ACTIVITY_RUNTIME + text[index:]
    block = function_block(text, "public func updateLocalInputActivity(")
    if "UserDefaults.standard" in block:
        manager = block.find("        self.localInputActivityManager.transaction")
        require(manager >= 0, "Account local activity manager owner missing")
        opening = block.find("{") + 1
        replacement = (
            block[:opening]
            + "\n        // MARK: Jerkgram v1.2ZD BUILD137_ACTIVITY_FAST_PATH1\n"
            + "        if isPresent && JerkgramActivityGhostRuntime.shouldSuppress(activity) {\n"
            + "            return\n"
            + "        }\n\n"
            + block[manager:]
        )
        text = text.replace(block, replacement, 1)
    return text


def patch_managed_activity(text: str) -> str:
    block = function_block(text, "private func requestActivity(")
    if "UserDefaults.standard" not in block:
        return text
    marker = block.find("    // MARK: GhostBase v0.5C Activity Ghost lower-layer guard")
    require(marker >= 0, "lower-layer Activity Ghost marker missing")
    stock = block.find("\n    return ", marker)
    require(stock >= 0, "lower-layer Activity Ghost stock continuation missing")
    fast = '''    // MARK: Jerkgram v1.2ZD BUILD137_ACTIVITY_FAST_PATH1
    if let activity, JerkgramActivityGhostRuntime.shouldSuppress(activity) {
        return .complete()
    }
'''
    updated = block[:marker] + fast + block[stock:]
    return text.replace(block, updated, 1)


def patch_shared_account_context(text: str) -> str:
    block = function_block(text, "private func jerkgramBuild135ProjectAccountSettings(")
    if "JerkgramActivityGhostRuntime.invalidate()" in block:
        return text
    insertion = block.rfind("}")
    require(insertion >= 0, "account projection closing brace missing")
    block = block[:insertion] + "    JerkgramActivityGhostRuntime.invalidate()\n" + block[insertion:]
    return text.replace(function_block(text, "private func jerkgramBuild135ProjectAccountSettings("), block, 1)


PRESENCE_GATE = r'''// MARK: Jerkgram v1.2ZD BUILD137_PRESENCE_GATE1
private final class JerkgramBuild137PresenceGate {
    static let shared = JerkgramBuild137PresenceGate()
    private let lock = NSLock()
    private let limit = 4096
    private var transitions: [String: String] = [:]
    private var users: [String: (signature: String, timestamp: Int64)] = [:]

    func shouldRecordTransition(key: String, transition: String) -> Bool {
        self.lock.lock()
        defer { self.lock.unlock() }
        if self.transitions[key] == transition { return false }
        if self.transitions[key] == nil && self.transitions.count >= self.limit {
            self.transitions.removeAll(keepingCapacity: true)
        }
        self.transitions[key] = transition
        return true
    }

    func shouldRefreshUser(key: String, signature: String, now: Int64) -> Bool {
        self.lock.lock()
        defer { self.lock.unlock() }
        if let cached = self.users[key], cached.signature == signature, now - cached.timestamp < 300 {
            return false
        }
        if self.users[key] == nil && self.users.count >= self.limit {
            self.users.removeAll(keepingCapacity: true)
        }
        self.users[key] = (signature, now)
        return true
    }
}

'''


def patch_presence_runtime(text: str) -> str:
    if "private enum GhostBasePresenceStoreV11G" in text:
        require("minimumKnownUserWriteInterval" in text, "modern presence write gate missing")
        require("loadedHistoryKeys" in text and "loadedKnownUserKeys" in text, "modern presence cache missing")
        summary_write = re.compile(
            r"\n\s*defaults\.set\(\s*"
            r'"(?:История присутствия|Известные пользователи):[^\"]*"\s*,\s*'
            r'forKey:\s*"jerkgram\.Runtime\.(?:PresenceSummary|KnownUsersSummary)\.V11G"\s*\)',
            flags=re.MULTILINE,
        )
        return summary_write.sub("", text)
    require("GhostBase v1.1B PRESENCEGLOBAL2 transition archive" in text, "presence transition baseline missing")
    if "BUILD137_PRESENCE_GATE1" not in text:
        anchor = "// MARK: GhostBase v1.1B PRESENCEGLOBAL2 transition archive\n"
        text = text.replace(anchor, anchor + PRESENCE_GATE, 1)

    presence = function_block(text, "private func ghostBaseRecordPresence(")
    if "shouldRecordTransition" not in presence:
        events = presence.find("    var events: [GhostBasePresenceHistoryEvent] = []")
        require(events >= 0, "presence event storage owner missing")
        gate = '''    let jerkgramTransition = ghostBasePresenceTransitionKey(event)
    guard JerkgramBuild137PresenceGate.shared.shouldRecordTransition(
        key: key,
        transition: jerkgramTransition
    ) else {
        return
    }
'''
        presence = presence[:events] + gate + presence[events:]
        text = text.replace(function_block(text, "private func ghostBaseRecordPresence("), presence, 1)

    user = function_block(text, "private func ghostBaseRegisterKnownUser(")
    if "shouldRefreshUser" not in user:
        decoder = user.find("    let decoder = JSONDecoder()")
        require(decoder >= 0, "known-user decoder owner missing")
        gate = r'''    let jerkgramIdentity = "\(user.nameOrPhone)|\(user.addressName ?? "")|bot=\(user.botInfo != nil)"
    guard JerkgramBuild137PresenceGate.shared.shouldRefreshUser(
        key: key,
        signature: jerkgramIdentity,
        now: now
    ) else {
        return
    }
'''
        user = user[:decoder] + gate + user[decoder:]
        text = text.replace(function_block(text, "private func ghostBaseRegisterKnownUser("), user, 1)
    return text


def patch_file(path: Path, transform, required: bool = True) -> None:
    if not path.is_file():
        require(not required, "missing materialized source: " + str(path))
        return
    original = path.read_text(encoding="utf-8")
    updated = transform(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")


def main() -> None:
    patch_file(APP_DELEGATE, patch_app_delegate_memory)
    patch_file(RAM_ROOT, patch_ram_root)
    patch_file(SETTINGS, patch_settings)
    patch_file(GLASS, patch_glass_runtime)
    patch_file(BLOCKED_POLICY, patch_blocked_policy)
    patch_file(CHAT_LIST, patch_chat_list_helper)
    patch_file(STATE, patch_runtime_diagnostics)
    patch_file(CONSUME, strip_legacy_diagnostic_writes)
    patch_file(ACCOUNT, patch_account_activity)
    patch_file(MANAGED_ACTIVITY, patch_managed_activity)
    patch_file(SHARED_ACCOUNT_CONTEXT, patch_shared_account_context)
    patch_file(UPDATE_PEERS, patch_presence_runtime)
    print("[Build137 performance] SOURCE PATCHED")
    print("[Build137 performance] shared RAM sampling off-main + specific invalidation + cached policy/glass + stable visibility cache + release diagnostics removed")


if __name__ == "__main__":
    main()
