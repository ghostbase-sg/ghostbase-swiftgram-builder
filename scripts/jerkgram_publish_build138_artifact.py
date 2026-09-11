#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys

import jerkgram_publish_build122_artifact as base


# The canonical workflow still references the historical Build138 artifact paths;
# keep those filenames stable for CI compatibility, but verify/publish Build140
# identity inside the IPA and metadata.
base.EXPECTED_BUILD = "140"
base.OUTPUT_IPA = Path("artifacts/Jerkgram-Build138.ipa")
base.OUTPUT_INFO = Path("artifacts/Jerkgram-Build138-info.txt")
FINAL_VERIFY = Path("scripts/verify_jerkgram_v12w_build133_final_ipa.py")


def verify(path: Path) -> None:
    subprocess.run([sys.executable, str(FINAL_VERIFY), str(path)], check=True)


def main() -> None:
    source = next((path for path in base.SOURCE_CANDIDATES if path.is_file()), None)
    base.require(source is not None, "final IPA source missing")
    verify(source)
    base.main()
    verify(base.OUTPUT_IPA)

    info = base.OUTPUT_INFO.read_text(encoding="utf-8")
    info = info.replace("Build=122", "Build=140")
    info += (
        "BundleID=com.jerkgram.ios\n"
        "TelegramVersion=12.9.2\n"
        "JerkgramVersion=1.0.2\n"
        "JerkgramTechnicalVersion=1.0.2\n"
        "TelemetryVersion=2.1\n"
    )
    base.OUTPUT_INFO.write_text(info, encoding="utf-8")
    print("[Build140 artifact] CFBundleVersion 140 and stable public identity verified before and after publication")


if __name__ == "__main__":
    main()
