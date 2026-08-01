#!/usr/bin/env python3
"""Guarded source audit for the Xash3D FWGS N64 bring-up.

r16 deliberately audits *structure*, not historical enum numbers. r9 stopped
before source integration because library-suffix changed numeric enum values
while preserving the API/layout we actually depend on.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
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
        "#elif XASH_PSP",
        "#define XASH_PLATFORM PLATFORM_PSP",
        "#elif XASH_MIPS",
        "#define XASH_ARCHITECTURE ARCHITECTURE_MIPS",
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


def numeric_define(path: Path, name: str) -> tuple[bool, str]:
    if not path.is_file():
        return False, f"FAIL enum audit: missing {path}"
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(rf"(?m)^\s*#\s*define\s+{re.escape(name)}\s+([0-9]+)\s*(?://.*)?$", text)
    if not m:
        return False, f"FAIL enum audit: numeric {name} define not found"
    return True, f"PASS enum audit: {name}={m.group(1)} (value is discovered, not hard-coded)"


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

    for name in ("PLATFORM_PSP", "ARCHITECTURE_MIPS"):
        ok, msg = numeric_define(paths["library suffix enums"], name)
        messages.append(msg)

    enums_text = paths["library suffix enums"].read_text(encoding="utf-8", errors="replace") if paths["library suffix enums"].is_file() else ""
    if re.search(r"(?m)^\s*#\s*define\s+PLATFORM_N64\b", enums_text):
        messages.append("NOTICE upstream already defines PLATFORM_N64; re-audit before applying our overlay")

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
