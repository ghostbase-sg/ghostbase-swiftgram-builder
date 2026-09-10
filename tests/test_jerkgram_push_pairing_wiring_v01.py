from pathlib import Path
import importlib.util
import unittest


ROOT = Path(__file__).parents[1]
INSTALLER = ROOT / "scripts/install_jerkgram_v12w_build133_probe_hook.py"
WORKFLOW = ROOT / ".github/workflows/build.yml"


def load_installer_module():
    spec = importlib.util.spec_from_file_location("build133_probe_hook", INSTALLER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativePairingWiringTests(unittest.TestCase):
    def test_push_click_and_pairing_bridges_are_wired_before_bazel(self):
        installer = INSTALLER.read_text()
        ordered = (
            "apply_jerkgram_push_click_bridge_v01.py",
            "verify_jerkgram_push_click_bridge_v01.py",
            "apply_jerkgram_push_pairing_bridge_v01.py",
            "verify_jerkgram_push_pairing_bridge_v01.py",
        )
        for name in ordered:
            self.assertEqual(installer.count(name), 1, f"{name} must be wired exactly once")

        positions = [installer.index(name) for name in ordered]
        self.assertEqual(positions, sorted(positions), "click bridge must precede pairing bridge and every apply must precede its verifier")

        module = load_installer_module()
        probe = (
            "header\n"
            + module.BUILD130_SOURCE_ANCHOR
            + "\n"
            + module.BAZEL_ANCHOR
            + " //Telegram:Telegram\n"
            + module.BUILD130_FINAL_ANCHOR
            + "\n"
        )
        generated = module.patch_probe(probe)
        generated_positions = [generated.index(name) for name in ordered]
        self.assertEqual(generated_positions, sorted(generated_positions))
        bazel_position = generated.index(module.BAZEL_ANCHOR)
        self.assertTrue(all(position < bazel_position for position in generated_positions))

    def test_release_workflow_preflights_new_native_bridge_scripts(self):
        workflow = WORKFLOW.read_text()
        for name in (
            "scripts/apply_jerkgram_push_click_bridge_v01.py",
            "scripts/verify_jerkgram_push_click_bridge_v01.py",
            "scripts/apply_jerkgram_push_pairing_bridge_v01.py",
            "scripts/verify_jerkgram_push_pairing_bridge_v01.py",
        ):
            self.assertIn(name, workflow)

        test_command = "python3 -m unittest tests.test_jerkgram_push_pairing_wiring_v01"
        self.assertIn(test_command, workflow)
        self.assertLess(
            workflow.index(test_command),
            workflow.index("python3 scripts/install_jerkgram_v12d_build115_probe_hook.py"),
        )


if __name__ == "__main__":
    unittest.main()
