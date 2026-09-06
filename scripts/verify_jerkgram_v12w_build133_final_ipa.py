#!/usr/bin/env python3

import verify_jerkgram_v12s_build130_final_ipa as base


base.base.base.EXPECTED_BUILD = "133"


def main() -> None:
    base.main()
    print("[Build133 final IPA verify] GREEN")


if __name__ == "__main__":
    main()
