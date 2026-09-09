#!/usr/bin/env python3

import apply_jerkgram_v12zd_build137_performance1 as patch


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build137 performance verify] " + message)


def main() -> None:
    owners = {
        "app_delegate": patch.APP_DELEGATE,
        "root": patch.RAM_ROOT,
        "settings": patch.SETTINGS,
        "glass": patch.GLASS,
        "policy": patch.BLOCKED_POLICY,
        "chat_list": patch.CHAT_LIST,
        "state": patch.STATE,
        "consume": patch.CONSUME,
        "account": patch.ACCOUNT,
        "managed_activity": patch.MANAGED_ACTIVITY,
        "shared_account": patch.SHARED_ACCOUNT_CONTEXT,
        "update_peers": patch.UPDATE_PEERS,
    }
    for name, path in owners.items():
        require(path.is_file(), f"missing {name} owner: {path}")

    app_delegate = owners["app_delegate"].read_text(encoding="utf-8")
    require(app_delegate.count(patch.MEMORY_SAMPLER_MARKER) == 1, "shared memory sampler marker count")
    require('DispatchQueue(label: "jerkgram.memory.sampler", qos: .utility)' in app_delegate, "memory sampler is not on utility queue")
    require("private var completions: [String: (Int) -> Void] = [:]" in app_delegate, "memory callbacks are not coalesced by bounded consumer set")
    require("if self.isSampling" in app_delegate, "parallel memory samples are not coalesced")
    require("Queue.mainQueue().async" in app_delegate, "memory sampler callbacks do not return to main")
    launch = patch.function_block(
        app_delegate,
        patch.APP_LAUNCH_SIGNATURE,
    )
    require('sample(consumer: "appDelegate")' in launch, "AppDelegate does not use shared memory sampler")
    require("let value = getMemoryConsumption()" not in launch, "AppDelegate still samples memory on main")
    require("jerkgramMemoryTimer.tolerance = 0.25" in launch, "stock memory timer tolerance missing")

    root = owners["root"].read_text(encoding="utf-8")
    require(root.count(patch.MARKER) == 1, "RAM performance marker count")
    setup = patch.function_block(root, "private func ghostBaseSetupRamOverlay()")
    require("UserDefaults.didChangeNotification" not in setup, "RAM overlay still observes every defaults write")
    require(patch.RAM_NOTIFICATION in setup, "specific RAM preference notification missing")
    layout = patch.function_block(root, "override public func containerLayoutUpdated(")
    require("ghostBaseUpdateRamOverlayState()" not in layout, "layout still rebuilds RAM state")
    require("ghostBaseUpdateRamValue()" not in layout, "layout still samples RAM")
    update = patch.function_block(root, "private func ghostBaseUpdateRamValue()")
    require('sample(consumer: "ramOverlay")' in update, "RAM overlay does not use shared memory sampler")
    require("ghostBaseCurrentMemoryFootprint" not in root, "duplicate Root task_info helper survived")
    require("ghostBaseRamMeasurementQueue" not in root, "duplicate Root memory queue survived")
    require("ghostBaseRamMeasurementInFlight" not in root, "duplicate Root in-flight state survived")
    require("timer.tolerance" in root, "RAM timer tolerance missing")

    settings = owners["settings"].read_text(encoding="utf-8")
    require("GhostBaseGlassStyle.setEnabled(value)" in settings, "Glass cache is not updated by its switch")
    ram_case = patch.functionless_case_block(settings, "case GhostBaseKey.showRamUnderClock:")
    require(patch.RAM_NOTIFICATION in ram_case, "RAM switch does not notify its sole observer")

    glass = owners["glass"].read_text(encoding="utf-8")
    getter = patch.property_block(glass, "public static var isEnabled: Bool")
    require("UserDefaults.standard" not in getter, "Glass hot getter still reads defaults")
    require("enabledLock" in getter and "enabledValue" in getter, "Glass in-memory cache missing")

    policy = owners["policy"].read_text(encoding="utf-8")
    for signature in (
        "public static func hideBlockedReactions(",
        "public static func hideBlockedMessages(",
    ):
        block = patch.function_block(policy, signature)
        require("UserDefaults.standard" not in block, f"{signature} still reads defaults")
        require("settings(accountPeerId:" in block, f"{signature} does not use policy cache")

    chat_list = owners["chat_list"].read_text(encoding="utf-8")
    require("mustRefreshFallback" not in chat_list, "unchanged empty previews still force history scans")

    state = owners["state"].read_text(encoding="utf-8")
    diagnostics = patch.function_block(state, "static func record(_ event: String)")
    require("queue.async" not in diagnostics, "release diagnostic queue still receives events")
    require("UserDefaults.standard" not in diagnostics, "release diagnostics still persist")

    consume = owners["consume"].read_text(encoding="utf-8")
    require("OT1.OutgoingKeepBlocked.Count" not in consume, "one-time media diagnostic counter survived")
    require("OT1.OutgoingKeepPath" not in consume, "one-time media diagnostic path survived")

    account = owners["account"].read_text(encoding="utf-8")
    require(account.count("BUILD137_ACTIVITY_SNAPSHOT1") == 1, "Activity Ghost snapshot owner count")
    upper = patch.function_block(account, "public func updateLocalInputActivity(")
    require("UserDefaults.standard" not in upper, "upper activity path still reads defaults")
    require("JerkgramActivityGhostRuntime.shouldSuppress(activity)" in upper, "upper activity cache gate missing")
    managed = owners["managed_activity"].read_text(encoding="utf-8")
    lower = patch.function_block(managed, "private func requestActivity(")
    require("UserDefaults.standard" not in lower, "lower activity path still reads defaults")
    require("JerkgramActivityGhostRuntime.shouldSuppress(activity)" in lower, "lower activity cache gate missing")
    persist = patch.function_block(settings, "private func jerkgramPersistChangedSettings(")
    require("JerkgramActivityGhostRuntime.invalidate()" in persist, "settings do not invalidate Activity Ghost snapshot")
    shared = owners["shared_account"].read_text(encoding="utf-8")
    projection = patch.function_block(shared, "private func jerkgramBuild135ProjectAccountSettings(")
    require("JerkgramActivityGhostRuntime.invalidate()" in projection, "account switch does not invalidate Activity Ghost snapshot")

    update_peers = owners["update_peers"].read_text(encoding="utf-8")
    if "private enum GhostBasePresenceStoreV11G" in update_peers:
        require("minimumKnownUserWriteInterval: Int64 = 6 * 60 * 60" in update_peers, "modern known-user write gate missing")
        require("loadedHistoryKeys" in update_peers and "loadedKnownUserKeys" in update_peers, "modern presence caches missing")
        require("maximumEvents = 500" in update_peers and "maximumKnownUsers = 5000" in update_peers, "modern presence bounds missing")
        require("PresenceSummary.V11G" not in update_peers, "presence summary diagnostic write survived")
        require("KnownUsersSummary.V11G" not in update_peers, "known-user summary diagnostic write survived")
    else:
        require(update_peers.count("BUILD137_PRESENCE_GATE1") == 1, "presence gate owner count")
        presence = patch.function_block(update_peers, "private func ghostBaseRecordPresence(")
        require("shouldRecordTransition" in presence, "stable presence updates are not gated")
        require(presence.index("shouldRecordTransition") < presence.index("JSONDecoder"), "presence gate runs after JSON decode")
        known_user = patch.function_block(update_peers, "private func ghostBaseRegisterKnownUser(")
        require("shouldRefreshUser" in known_user, "known-user refresh is not throttled")
        require(known_user.index("shouldRefreshUser") < known_user.index("JSONDecoder"), "known-user gate runs after JSON decode")
        require("private let limit = 4096" in update_peers, "presence caches are not bounded")
    print("[Build137 performance verify] GREEN")


if __name__ == "__main__":
    main()
