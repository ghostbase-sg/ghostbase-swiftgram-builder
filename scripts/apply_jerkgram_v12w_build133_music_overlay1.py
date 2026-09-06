#!/usr/bin/env python3

from pathlib import Path
import os
import subprocess


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
PINNED_OFFICIAL_COMMIT = "6ad963e5b62d354da79040f388ae2b9132fb17b8"
CONTROLLER_REL = "submodules/TelegramUI/Sources/OverlayAudioPlayerController.swift"
NODE_REL = "submodules/TelegramUI/Sources/OverlayAudioPlayerControllerNode.swift"
CONTROLLER = ROOT / CONTROLLER_REL
NODE = ROOT / NODE_REL
MARKER = "// MARK: Jerkgram v1.2W BUILD133_NATIVE_MUSIC_MATERIAL1"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 music overlay] " + message)


def replace_exact(text: str, old: str, new: str, label: str, expected: int = 1) -> str:
    count = text.count(old)
    require(count == expected, f"{label}: expected {expected} anchor(s), found {count}")
    return text.replace(old, new)


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    require(result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def official_source(relative_path: str) -> str:
    return git_output("show", f"{PINNED_OFFICIAL_COMMIT}:{relative_path}")


def apply_native_material(text: str) -> str:
    require("final class OverlayAudioPlayerControllerNode: ViewControllerTracingNode" in text, "native node owner missing")
    require("OverlayAudioPlayerControlsNode(" in text, "native controls owner missing")
    require("ChatHistoryListNodeImpl(" in text, "native playlist/history owner missing")
    require("systemStyle: .glass" in text, "native Telegram glass history style missing")
    require("UIVisualEffectView()" in text, "native album-art material owner missing")
    require(MARKER not in text, "material marker already exists in Official source")

    text = replace_exact(
        text,
        "final class OverlayAudioPlayerControllerNode: ViewControllerTracingNode, ASGestureRecognizerDelegate {\n",
        "final class OverlayAudioPlayerControllerNode: ViewControllerTracingNode, ASGestureRecognizerDelegate {\n    " + MARKER + "\n",
        "node class marker",
    )
    text = replace_exact(
        text,
        "        self.dimNode.backgroundColor = UIColor(white: 0.0, alpha: 0.5)\n",
        "        self.dimNode.backgroundColor = UIColor(white: 0.0, alpha: 0.18)\n",
        "native dim layer",
    )
    text = replace_exact(
        text,
        "        self.historyBackgroundContentNode.backgroundColor = self.presentationData.theme.list.itemModalBlocksBackgroundColor\n",
        "        self.historyBackgroundContentNode.backgroundColor = self.presentationData.theme.list.itemModalBlocksBackgroundColor.withAlphaComponent(0.94)\n",
        "initial history material",
    )

    for owner in ("historyFrameLeftOverlayNode", "historyFrameRightOverlayNode", "historyFrameTopOverlayNode"):
        text = replace_exact(
            text,
            f"        self.{owner}.backgroundColor = self.presentationData.theme.list.modalBlocksBackgroundColor\n",
            f"        self.{owner}.backgroundColor = self.presentationData.theme.list.modalBlocksBackgroundColor.withAlphaComponent(0.94)\n",
            f"initial {owner}",
        )

    text = replace_exact(
        text,
        "        self.historyBackgroundContentNode.backgroundColor = self.hasAnyHistoryMessages == true ? self.presentationData.theme.list.itemModalBlocksBackgroundColor : self.presentationData.theme.list.modalPlainBackgroundColor\n",
        "        self.historyBackgroundContentNode.backgroundColor = self.hasAnyHistoryMessages == true ? self.presentationData.theme.list.itemModalBlocksBackgroundColor.withAlphaComponent(0.94) : self.presentationData.theme.list.modalPlainBackgroundColor.withAlphaComponent(0.94)\n",
        "updated history material",
    )

    for owner in ("historyFrameLeftOverlayNode", "historyFrameRightOverlayNode", "historyFrameTopOverlayNode"):
        text = replace_exact(
            text,
            f"        self.{owner}.backgroundColor = self.hasAnyHistoryMessages == true ? self.presentationData.theme.list.modalBlocksBackgroundColor : self.presentationData.theme.list.modalPlainBackgroundColor\n",
            f"        self.{owner}.backgroundColor = self.hasAnyHistoryMessages == true ? self.presentationData.theme.list.modalBlocksBackgroundColor.withAlphaComponent(0.94) : self.presentationData.theme.list.modalPlainBackgroundColor.withAlphaComponent(0.94)\n",
            f"updated {owner}",
        )

    text = replace_exact(
        text,
        "        context.setFillColor(theme.list.modalBlocksBackgroundColor.cgColor)\n",
        "        context.setFillColor(theme.list.modalBlocksBackgroundColor.withAlphaComponent(0.94).cgColor)\n",
        "native top-corner material",
    )
    return text


def main() -> None:
    require(CONTROLLER.is_file(), "controller owner missing: " + str(CONTROLLER))
    require(NODE.is_file(), "node owner missing: " + str(NODE))

    head = git_output("rev-parse", "HEAD").strip()
    require(head == PINNED_OFFICIAL_COMMIT, f"unexpected Telegram checkout HEAD {head}")

    official_controller = official_source(CONTROLLER_REL)
    official_node = official_source(NODE_REL)
    require("final class OverlayAudioPlayerControllerImpl: ViewController, OverlayAudioPlayerController" in official_controller, "Official controller implementation missing")

    patched_node = apply_native_material(official_node)

    # These files are dedicated Telegram overlay owners. Restore them from the
    # exact pinned Official tree first so historical clone/backdrop/player code
    # cannot survive, then apply only the bounded native material adaptation.
    CONTROLLER.write_text(official_controller, encoding="utf-8")
    NODE.write_text(patched_node, encoding="utf-8")

    print("[Build133 music overlay] SOURCE PATCHED")


if __name__ == "__main__":
    main()
