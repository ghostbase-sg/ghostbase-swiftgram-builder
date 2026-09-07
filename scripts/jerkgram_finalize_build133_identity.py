#!/usr/bin/env python3

import jerkgram_finalize_build130_identity as base


BUILD = "133"
PUBLIC_BUNDLE = "ph.telegra.Telegraph"
TELEGRAM_VERSION = "12.9.2"
JERKGRAM_DISPLAY_VERSION = "1.0.2 Beta 1"
JERKGRAM_TECHNICAL_VERSION = "1.0.2-beta.1"

# Build130 -> Build128 -> Build122 owns the actual IPA stamping. Keep its exact
# public Telegram bundle contract and only advance CFBundleVersion to 133.
base.base.base.BUILD = BUILD
base.base.base.PUBLIC_BUNDLE = PUBLIC_BUNDLE


def main() -> None:
    base.main()
    print("[Build133 identity] GREEN")
    print("[Build133 identity] ph.telegra.Telegraph / CFBundleShortVersionString preserved as Telegram 12.9.2 / CFBundleVersion=133")
    print("[Build133 identity] in-app Jerkgram release: 1.0.2 Beta 1 (1.0.2-beta.1)")


if __name__ == "__main__":
    main()
