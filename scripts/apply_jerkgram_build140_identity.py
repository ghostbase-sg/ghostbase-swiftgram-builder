#!/usr/bin/env python3
from pathlib import Path
import os

ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
STRINGS = ROOT / "submodules/TelegramPresentationData/Sources/JerkgramStrings.swift"
ENUM = "public enum JerkgramReleaseIdentity {"
OLD_BUILD = 'public static let build = "139"'
NEW_BUILD = 'public static let build = "140"'


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build140 identity] " + message)


def enum_scope(text: str) -> tuple[int, int]:
    start = text.find(ENUM)
    require(start >= 0, "JerkgramReleaseIdentity missing")
    require(text.count(ENUM) == 1, "JerkgramReleaseIdentity is ambiguous")
    brace = text.find("{", start)
    depth = 0
    in_string = False
    escaped = False
    for index in range(brace, len(text)):
        ch = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1
    raise RuntimeError("[Build140 identity] unbalanced JerkgramReleaseIdentity")


def verify_transformed(text: str) -> None:
    start, end = enum_scope(text)
    scope = text[start:end]
    for token in (
        'public static let displayVersion = "1.0.2"',
        'public static let technicalVersion = "1.0.2"',
        NEW_BUILD,
        'public static let telegramBase = "12.9.2"',
    ):
        require(token in scope, "release identity token missing: " + token)
    require(OLD_BUILD not in scope, "Build139 identity survived Build140 overlay")
    require("Beta" not in scope and "beta" not in scope, "public version unexpectedly became beta")


def patch_text(text: str) -> str:
    start, end = enum_scope(text)
    scope = text[start:end]
    if NEW_BUILD in scope:
        require(scope.count(NEW_BUILD) == 1, "Build140 identity is ambiguous")
        verify_transformed(text)
        return text
    require(scope.count(OLD_BUILD) == 1, "expected exactly one Build139 identity to advance")
    scope = scope.replace(OLD_BUILD, NEW_BUILD, 1)
    updated = text[:start] + scope + text[end:]
    verify_transformed(updated)
    return updated


def main() -> None:
    require(STRINGS.is_file(), "JerkgramStrings missing: " + str(STRINGS))
    updated = patch_text(STRINGS.read_text(encoding="utf-8"))
    STRINGS.write_text(updated, encoding="utf-8")
    print("[Build140 identity] SOURCE PATCHED")
    print("[Build140 identity] Jerkgram 1.0.2 / Build 140 / Telegram Base 12.9.2")


if __name__ == "__main__":
    main()
