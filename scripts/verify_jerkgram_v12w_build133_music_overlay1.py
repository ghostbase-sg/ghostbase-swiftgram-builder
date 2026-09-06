#!/usr/bin/env python3

from pathlib import Path
import importlib.util
import os


ROOT = Path(os.environ.get("JERKGRAM_SOURCE_ROOT", os.environ.get("GHOSTBASE_SOURCE_ROOT", str(Path.cwd())))).resolve()
BUILDER_ROOT = Path(__file__).resolve().parents[1]
PATCH_PATH = BUILDER_ROOT / "scripts" / "apply_jerkgram_v12w_build133_music_overlay1.py"


def load_patch():
    spec = importlib.util.spec_from_file_location("build133_music_patch", PATCH_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("[Build133 music verifier] " + message)


def main() -> None:
    patch = load_patch()
    controller = ROOT / patch.CONTROLLER_REL
    node = ROOT / patch.NODE_REL
    require(controller.is_file(), "materialized controller owner missing")
    require(node.is_file(), "materialized node owner missing")

    official_controller = patch.official_source(patch.CONTROLLER_REL)
    official_node = patch.official_source(patch.NODE_REL)
    expected_node = patch.apply_native_material(official_node)

    actual_controller = controller.read_text(encoding="utf-8")
    actual_node = node.read_text(encoding="utf-8")

    # Controller must stay completely native. The node may differ from Official
    # only by apply_native_material(), which is checked as an exact full-file equality.
    require(actual_controller == official_controller, "controller differs from pinned Official owner")
    require(actual_node == expected_node, "node contains changes outside bounded native material transform")
    require(actual_node.count(patch.MARKER) == 1, "material marker count != 1")

    required_native = (
        "OverlayAudioPlayerControlsNode(",
        "ChatHistoryListNodeImpl(",
        "systemStyle: .glass",
        "UIVisualEffectView()",
        "requestDismiss",
        "requestShare",
        "requestSearchByArtist",
    )
    for token in required_native:
        require(token in actual_node, "native overlay owner missing token: " + token)

    forbidden = (
        "GhostBaseMusicProfileBackdropView",
        "snapshotView(",
        "drawHierarchy(",
        "AVPlayer(",
        "UniversalVideoNode(",
        "CADisplayLink(",
        "CIImage(",
    )
    joined = actual_controller + "\n" + actual_node
    for token in forbidden:
        require(token not in joined, "forbidden replacement/rendering path survived: " + token)

    require("UIColor(white: 0.0, alpha: 0.5)" not in actual_node, "stock heavy dim survived")
    require("UIColor(white: 0.0, alpha: 0.18)" in actual_node, "bounded dim adaptation missing")
    require(actual_node.count("withAlphaComponent(0.94)") == 9, "native translucent material anchor count != 9")

    print("[Build133 music verifier] PREFLIGHT GREEN")


if __name__ == "__main__":
    main()
