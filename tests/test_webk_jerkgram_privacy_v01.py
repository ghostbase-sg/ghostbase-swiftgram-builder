from pathlib import Path
import subprocess
import sys


def test_privacy_patch_removes_sensitive_push_logs(tmp_path: Path):
    root = tmp_path / "tweb"
    manager = root / "src/lib/appManagers/pushSingleManager.ts"
    sw_push = root / "src/lib/serviceWorker/push.ts"
    manager.parent.mkdir(parents=True)
    sw_push.parent.mkdir(parents=True)

    manager.write_text(
        "this.log('register device', this.registeredDevice, tokenData, userIds);\n"
        "this.log('unregister device', tokenData);\n"
    )
    sw_push.write_text(
        "log('push', copy);\n"
        "log.error('push notification error', err, copy);\n"
        "log('encrypted push', obj);\n"
        "log('on notification click', notification);\n"
        "log('show notify', title, body, obj, notificationOptions);\n"
    )

    patcher = Path(__file__).parents[1] / "webpush-companion/apply_webk_jerkgram_privacy_v01.py"
    result = subprocess.run([sys.executable, str(patcher), str(root)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout

    manager_text = manager.read_text()
    assert "this.registeredDevice, tokenData, userIds" not in manager_text
    assert "unregister device', tokenData" not in manager_text
    assert "tokenType: tokenData.tokenType" in manager_text
    assert "accounts: userIds.length" in manager_text

    sw_text = sw_push.read_text()
    assert "log('push', copy)" not in sw_text
    assert "err, copy" not in sw_text
    assert "log('encrypted push', obj)" not in sw_text
    assert "notification click', notification" not in sw_text
    assert "title, body, obj, notificationOptions" not in sw_text
    assert "log('push received')" in sw_text
    assert "log('show notification')" in sw_text
