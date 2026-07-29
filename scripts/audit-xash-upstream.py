#!/usr/bin/env python3
"""Guarded source audit for the Xash3D FWGS N64 bring-up.

This script DOES NOT modify upstream. It verifies the exact current-upstream
assumptions that r9 changes or relies on. Failing loudly on drift is intentional.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

CHECKS = {
    "root wscript": [
        "Subproject('filesystem')",
        "Subproject('3rdparty/library_suffix')",
        "conf.load('xshlib xcompile compiler_c compiler_cxx')",
        "if conf.options.NSWITCH:",
        "if conf.options.PSVITA:",
        "conf.options.LOW_MEMORY",
    ],
    "engine wscript": [
        "--enable-static-binary",
        "check_pthreads(mode='c')",
        "platform/%s/*.c",
        "platform/posix/*.c",
        "get_tgen_by_name('filesystem_stdio')",
    ],
    "platform header": [
        "double Platform_DoubleTime",
        "NSwitch_Init",
        "PSVita_Init",
    ],
    "library suffix build": [
        "#undef XASH_NSWITCH",
        "#elif defined __psp__",
        "#else // POSIX compatible",
        "#elif defined __mips__",
    ],
    "library suffix enums": [
        "#define PLATFORM_PSP 18",
        "#elif XASH_PSP",
        "#define ARCHITECTURE_MIPS 4",
    ],
    "xshlib static helper": [
        "--static-linking",
        "find_program('ld')",
        "find_program('objcopy')",
        "class cprogram_static",
    ],
}


def require_text(path: Path, needles: list[str], label: str) -> list[str]:
    if not path.is_file():
        return [f"FAIL {label}: missing {path}"]
    text = path.read_text(encoding="utf-8", errors="replace")
    out: list[str] = []
    for needle in needles:
        if needle in text:
            out.append(f"PASS {label}: found {needle!r}")
        else:
            out.append(f"FAIL {label}: expected {needle!r}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("xash_root", type=Path)
    args = parser.parse_args()
    root = args.xash_root.resolve()

    paths = {
        "root wscript": root / "wscript",
        "engine wscript": root / "engine" / "wscript",
        "platform header": root / "engine" / "platform" / "platform.h",
        "library suffix build": root / "3rdparty" / "library_suffix" / "include" / "build.h",
        "library suffix enums": root / "3rdparty" / "library_suffix" / "include" / "buildenums.h",
        "xshlib static helper": root / "scripts" / "waifulib" / "xshlib.py",
    }

    messages: list[str] = []
    for label, needles in CHECKS.items():
        messages.extend(require_text(paths[label], needles, label))

    n64_dir = root / "engine" / "platform" / "n64"
    if n64_dir.exists():
        messages.append("NOTICE upstream already has engine/platform/n64; re-audit before applying our overlay")
    else:
        messages.append("PASS upstream has no engine/platform/n64 yet")

    for line in messages:
        print(line)

    failures = sum(line.startswith("FAIL") for line in messages)
    print(f"\nAudit result: {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
