#!/usr/bin/env python3

import jerkgram_finalize_build130_identity as base


BUILD = "134"
PUBLIC_BUNDLE = "com.jerkgram.ios"
TELEGRAM_VERSION = "12.9.2"
JERKGRAM_DISPLAY_VERSION = "1.0.2 Beta 2"
JERKGRAM_TECHNICAL_VERSION = "1.0.2-beta.2"

# The last-good run 34040990849 is the release identity baseline:
# Telegram 12.9.2 / Jerkgram display name; Build134 switches the public bundle.
# Keep that exact public identity and advance only Build/Jerkgram release data.
base.base.base.BUILD = BUILD
base.base.base.PUBLIC_BUNDLE = PUBLIC_BUNDLE


def main() -> None:
    base.main()
    print("[Build134 identity] GREEN")
    print("[Build134 identity] com.jerkgram.ios / CFBundleShortVersionString=12.9.2 / CFBundleVersion=134")
    print("[Build134 identity] in-app Jerkgram release: 1.0.2 Beta 2 (1.0.2-beta.2)")


if __name__ == "__main__":
    main()
