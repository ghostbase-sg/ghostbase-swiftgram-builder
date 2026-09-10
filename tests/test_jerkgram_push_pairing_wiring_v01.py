from pathlib import Path


ROOT = Path(__file__).parents[1]
INSTALLER = ROOT / "scripts/install_jerkgram_v12w_build133_probe_hook.py"
WORKFLOW = ROOT / ".github/workflows/build.yml"


def test_push_click_and_pairing_bridges_are_wired_before_bazel():
    installer = INSTALLER.read_text()

    ordered = (
        "apply_jerkgram_push_click_bridge_v01.py",
        "verify_jerkgram_push_click_bridge_v01.py",
        "apply_jerkgram_push_pairing_bridge_v01.py",
        "verify_jerkgram_push_pairing_bridge_v01.py",
    )
    for name in ordered:
        assert installer.count(name) == 1, f"{name} must be wired exactly once"

    positions = [installer.index(name) for name in ordered]
    assert positions == sorted(positions), "click bridge must precede pairing bridge and every apply must precede its verifier"

    # The Build133/138 probe installer emits SOURCE_ORDERED before the Bazel anchor.
    assert installer.index("apply_jerkgram_push_click_bridge_v01.py") < installer.index('BAZEL_ANCHOR =')


def test_release_workflow_preflights_new_native_bridge_scripts():
    workflow = WORKFLOW.read_text()
    for name in (
        "scripts/apply_jerkgram_push_click_bridge_v01.py",
        "scripts/verify_jerkgram_push_click_bridge_v01.py",
        "scripts/apply_jerkgram_push_pairing_bridge_v01.py",
        "scripts/verify_jerkgram_push_pairing_bridge_v01.py",
    ):
        assert name in workflow

    # Wiring tests are cheap and must run before the canonical materialization/Bazel step.
    test_command = "python3 -m unittest tests.test_jerkgram_push_pairing_wiring_v01"
    assert test_command in workflow
    assert workflow.index(test_command) < workflow.index("python3 scripts/install_jerkgram_v12d_build115_probe_hook.py")
