#!/usr/bin/env python3
"""Apply the consolidated r12 Nintendo 64 source changes to pristine Xash3D FWGS.

One source integration pass only. No generated-patch chain, no sed/regex mutation,
and no edits to Xash's generated/minified xcompile.py. Each source edit is guarded
by a unique audited block from current upstream and aborts on drift.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: {label}: expected exactly 1 audited block, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched {path}: {label}")


def patch_root_wscript(root: Path) -> None:
    p = root / "wscript"

    replace_once(
        p,
        "\tgrp.add_option('-d', '--dedicated', action = 'store_true', dest = 'DEDICATED', default = False,\n"
        "\t\thelp = 'only build Xash Dedicated Server [default: %(default)s]')\n",
        "\tgrp.add_option('-d', '--dedicated', action = 'store_true', dest = 'DEDICATED', default = False,\n"
        "\t\thelp = 'only build Xash Dedicated Server [default: %(default)s]')\n"
        "\tgrp.add_option('--n64', action = 'store_true', dest = 'N64', default = False,\n"
        "\t\thelp = 'build the Nintendo 64/libdragon target [default: %(default)s]')\n",
        "add --n64 option",
    )

    replace_once(
        p,
        "\t# Load compilers early\n\tconf.load('xshlib xcompile compiler_c compiler_cxx')\n\n",
        "\t# Load compilers early\n\tconf.load('xshlib xcompile compiler_c compiler_cxx')\n\n"
        "\tif conf.options.N64:\n"
        "\t\t# The build driver supplies libdragon's mips64-elf GCC explicitly.\n"
        "\t\t# Do not pretend N64 is Linux/POSIX or modify xcompile.py.\n"
        "\t\tn64_inst = conf.environ.get('N64_INST')\n"
        "\t\tif not n64_inst:\n"
        "\t\t\tconf.fatal('N64_INST must point to the libdragon toolchain root')\n"
        "\t\tn64_inc = os.path.join(n64_inst, 'mips64-elf', 'include')\n"
        "\t\tn64_lib = os.path.join(n64_inst, 'mips64-elf', 'lib')\n"
        "\t\tcommon = [\n"
        "\t\t\t'-DN64', '-D__N64__', '-march=vr4300', '-mtune=vr4300', '-mabi=o64',\n"
        "\t\t\t'-I%s' % n64_inc, '-falign-functions=32', '-ffunction-sections', '-fdata-sections',\n"
        "\t\t\t'-ffast-math', '-ftrapping-math', '-fno-associative-math', '-ftrivial-auto-var-init=pattern',\n"
        "\t\t]\n"
        "\t\tconf.env.DEST_OS = 'n64'\n"
        "\t\tconf.env.DEST_CPU = 'mips'\n"
        "\t\tconf.env.DEST_BINFMT = 'elf'\n"
        "\t\tconf.env.append_unique('CFLAGS', common + ['-std=gnu17'])\n"
        "\t\tconf.env.append_unique('CXXFLAGS', common + ['-std=gnu++17'])\n"
        "\t\tconf.env.append_unique('LINKFLAGS', ['-mabi=o64', '-g', '-L%s' % n64_lib, '-Wl,-T,n64.ld', '-Wl,--gc-sections', '-Wl,--wrap=__do_global_ctors'])\n"
        "\t\tconf.env.append_unique('LDFLAGS', ['-ldragon', '-lm', '-ldragonsys'])\n"
        "\t\tconf.env.HAVE_M = True\n"
        "\t\tconf.env.LIB_M = ['m']\n\n",
        "configure libdragon toolchain flags",
    )

    replace_once(
        p,
        "\telif conf.env.DEST_OS == 'emscripten':\n\t\tconf.options.BUILD_BUNDLED_DEPS = True\n",
        "\telif conf.env.DEST_OS == 'n64':\n"
        "\t\tconf.options.LOW_MEMORY = 1\n"
        "\t\tconf.options.BUILD_BUNDLED_DEPS = True\n"
        "\telif conf.env.DEST_OS == 'emscripten':\n\t\tconf.options.BUILD_BUNDLED_DEPS = True\n",
        "N64 low-memory defaults",
    )

    replace_once(
        p,
        "\tif conf.options.ENABLE_RPATH and conf.env.DEST_OS not in ['nswitch', 'psvita']:",
        "\tif conf.options.ENABLE_RPATH and conf.env.DEST_OS not in ['nswitch', 'psvita', 'n64']:",
        "disable rpath on N64",
    )

    # Current upstream performs platform library probes later in configure(),
    # after the generic stdint/alloca checks. Match the unique solder probe,
    # not an assumed adjacency to XASH_GAMEDIR (the r10 failure).
    replace_once(
        p,
        "\tif conf.env.DEST_OS == 'nswitch':\n"
        "\t\tconf.check_cfg(package='solder', args='--cflags --libs', uselib_store='SOLDER')\n",
        "\tif conf.env.DEST_OS == 'n64':\n"
        "\t\t# libdragon/newlib and the final link line are supplied by the N64 target.\n"
        "\t\tpass\n"
        "\telif conf.env.DEST_OS == 'nswitch':\n"
        "\t\tconf.check_cfg(package='solder', args='--cflags --libs', uselib_store='SOLDER')\n",
        "skip host dl/platform library probes",
    )

    # Do not pre-emptively alter Xash's large-file feature probe. r10 never
    # reached configure, so we have no evidence that newlib needs an exception.
    # Let the real N64 compiler tell us at the next frontier.


def patch_engine_wscript(root: Path) -> None:
    p = root / "engine/wscript"
    replace_once(
        p,
        "\tif not conf.env.DEST_OS in ['win32', 'android']:\n\t\tconf.check_pthreads(mode='c')\n",
        "\tif not conf.env.DEST_OS in ['win32', 'android', 'n64']:\n\t\tconf.check_pthreads(mode='c')\n",
        "skip pthread probe",
    )
    replace_once(
        p,
        "\tif bld.env.DEST_OS not in ['win32', 'dos']:\n\t\tsource += bld.path.ant_glob('platform/posix/*.c')\n",
        "\tif bld.env.DEST_OS not in ['win32', 'dos', 'n64']:\n\t\tsource += bld.path.ant_glob('platform/posix/*.c')\n",
        "exclude POSIX backend",
    )
    replace_once(
        p,
        "\tif bld.env.DEST_OS == 'win32':\n\t\tlibs += ['USER32', 'SHELL32', 'GDI32', 'ADVAPI32', 'DBGHELP', 'PSAPI', 'WS2_32']\n",
        "\tif bld.env.DEST_OS == 'n64':\n"
        "\t\tlibs += ['M']\n"
        "\telif bld.env.DEST_OS == 'win32':\n\t\tlibs += ['USER32', 'SHELL32', 'GDI32', 'ADVAPI32', 'DBGHELP', 'PSAPI', 'WS2_32']\n",
        "use N64 link set instead of POSIX libraries",
    )


def patch_platform_header(root: Path) -> None:
    p = root / "engine/platform/platform.h"
    replace_once(
        p,
        "#if XASH_NSWITCH\nvoid NSwitch_Init( void );\nvoid NSwitch_Shutdown( void );\n#endif\n",
        "#if XASH_N64\nvoid N64_Init( void );\nvoid N64_Shutdown( void );\n#endif\n"
        "#if XASH_NSWITCH\nvoid NSwitch_Init( void );\nvoid NSwitch_Shutdown( void );\n#endif\n",
        "declare N64 platform hooks",
    )
    replace_once(
        p,
        "#if XASH_ANDROID\n\tAndroid_Init( );\n#elif XASH_NSWITCH\n",
        "#if XASH_N64\n\tN64_Init( );\n#elif XASH_ANDROID\n\tAndroid_Init( );\n#elif XASH_NSWITCH\n",
        "dispatch N64 init",
    )
    replace_once(
        p,
        "#if XASH_NSWITCH\n\tNSwitch_Shutdown( );\n",
        "#if XASH_N64\n\tN64_Shutdown( );\n#elif XASH_NSWITCH\n\tNSwitch_Shutdown( );\n",
        "dispatch N64 shutdown",
    )


def _unique_line_index(lines: list[str], stripped: str, label: str) -> int:
    matches = [i for i, line in enumerate(lines) if line.strip() == stripped]
    if len(matches) != 1:
        raise SystemExit(f"{label}: expected exactly 1 structural line {stripped!r}, found {len(matches)}")
    return matches[0]


def _next_nonblank(lines: list[str], start: int) -> int:
    for i in range(start, len(lines)):
        if lines[i].strip():
            return i
    raise SystemExit("unexpected end of file while finding next nonblank line")


def patch_library_suffix(root: Path) -> None:
    d = root / "3rdparty/library_suffix/include"
    build_h = d / "build.h"
    enums_h = d / "buildenums.h"
    if not build_h.is_file() or not enums_h.is_file():
        raise SystemExit("library_suffix submodule missing: clone Xash with --recursive")

    # build.h explicitly requires every XASH_* macro introduced by the file to
    # appear in its #undef list first. Keep this edit exact and independently
    # guarded.
    replace_once(build_h, "#undef XASH_NSWITCH\n", "#undef XASH_NSWITCH\n#undef XASH_N64\n", "declare XASH_N64")

    # r11 incorrectly assumed that the PSP branch was immediately adjacent to
    # the POSIX fallback. The audited contract we actually need is simpler:
    # N64 must be selected BEFORE the unique `#else // POSIX compatible` branch.
    # Preserve every existing platform branch verbatim and insert only our two
    # lines at that structural boundary.
    lines = build_h.read_text(encoding="utf-8").splitlines(keepends=True)
    posix_idx = _unique_line_index(lines, "#else // POSIX compatible", f"{build_h}: POSIX fallback")
    psp_elif = [i for i, line in enumerate(lines[:posix_idx]) if line.strip() == "#elif defined __psp__"]
    psp_define = [i for i, line in enumerate(lines[:posix_idx]) if line.strip() == "#define XASH_PSP 1"]
    if len(psp_elif) != 1 or len(psp_define) != 1 or psp_define[0] <= psp_elif[0]:
        raise SystemExit(f"{build_h}: audited PSP platform branch is not structurally recognizable")
    if any(line.strip() in {"#elif defined N64 || defined __N64__", "#define XASH_N64 1"} for line in lines):
        raise SystemExit(f"{build_h}: XASH_N64 platform detection already exists; re-audit instead of stacking edits")
    lines[posix_idx:posix_idx] = [
        "#elif defined N64 || defined __N64__\n",
        " #define XASH_N64 1\n",
    ]
    build_h.write_text("".join(lines), encoding="utf-8")
    print(f"patched {build_h}: insert N64 before audited POSIX fallback")

    # Never hard-code library_suffix's enum numbers. Discover the current
    # PLATFORM_* table, allocate the next free value, and append N64 to the
    # platform-number block without depending on which platform happens to be
    # last in this revision.
    enum_text = enums_h.read_text(encoding="utf-8")
    if re.search(r"(?m)^\s*#\s*define\s+PLATFORM_N64\b", enum_text):
        raise SystemExit("library_suffix already defines PLATFORM_N64; re-audit instead of overwriting it")
    enum_lines = enum_text.splitlines(keepends=True)
    platform_defs: list[tuple[int, str, int]] = []
    for i, line in enumerate(enum_lines):
        m = re.match(r"^\s*#\s*define\s+(PLATFORM_[A-Z0-9_]+)\s+([0-9]+)\s*(?://.*)?\s*$", line.rstrip("\n"))
        if m:
            platform_defs.append((i, m.group(1), int(m.group(2))))
    if not platform_defs:
        raise SystemExit(f"{enums_h}: no numeric PLATFORM_* defines found")
    if not any(name == "PLATFORM_PSP" for _, name, _ in platform_defs):
        raise SystemExit(f"{enums_h}: PLATFORM_PSP anchor missing")
    n64_platform_id = max(value for _, _, value in platform_defs) + 1
    last_platform_line = max(i for i, _, _ in platform_defs)
    enum_lines[last_platform_line + 1:last_platform_line + 1] = [f"#define PLATFORM_N64 {n64_platform_id}\n"]

    # Locate the PSP dispatch semantically rather than requiring it to be
    # adjacent to the final #else. This survives new platform branches being
    # inserted before or after PSP while still validating the exact mapping we
    # are extending.
    psp_dispatch_candidates: list[tuple[int, int]] = []
    for i, line in enumerate(enum_lines):
        if line.strip() != "#elif XASH_PSP":
            continue
        j = _next_nonblank(enum_lines, i + 1)
        if enum_lines[j].strip() == "#define XASH_PLATFORM PLATFORM_PSP":
            psp_dispatch_candidates.append((i, j))
    if len(psp_dispatch_candidates) != 1:
        raise SystemExit(f"{enums_h}: expected exactly one PSP platform dispatch, found {len(psp_dispatch_candidates)}")
    _, psp_define_idx = psp_dispatch_candidates[0]
    enum_lines[psp_define_idx + 1:psp_define_idx + 1] = [
        "#elif XASH_N64\n",
        " #define XASH_PLATFORM PLATFORM_N64\n",
    ]
    enums_h.write_text("".join(enum_lines), encoding="utf-8")
    print(f"patched {enums_h}: add N64 platform enum as {n64_platform_id} and map XASH_N64 structurally")

def install_backend(root: Path, overlay: Path) -> None:
    src = overlay / "engine/platform/n64/sys_n64.c"
    dst = root / "engine/platform/n64/sys_n64.c"
    if not src.is_file():
        raise SystemExit(f"missing N64 backend overlay: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise SystemExit(f"upstream already has {dst}; re-audit instead of overwriting it")
    shutil.copy2(src, dst)
    print(f"installed {dst}")


def verify(root: Path) -> None:
    checks = {
        root / "wscript": ["--n64", "DEST_OS = 'n64'", "-Wl,-T,n64.ld", "LOW_MEMORY = 1"],
        root / "engine/wscript": ["'android', 'n64'", "'win32', 'dos', 'n64'", "DEST_OS == 'n64'"],
        root / "engine/platform/platform.h": ["N64_Init", "N64_Shutdown"],
        root / "3rdparty/library_suffix/include/build.h": ["XASH_N64", "defined N64 || defined __N64__"],
        root / "3rdparty/library_suffix/include/buildenums.h": ["PLATFORM_N64", "XASH_PLATFORM PLATFORM_N64"],
        root / "engine/platform/n64/sys_n64.c": ["debug_init_sdfs", "sd:/xash"],
    }
    for path, needles in checks.items():
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                raise SystemExit(f"verification failed: {needle!r} missing from {path}")
    print("r12 N64 source integration verification: PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("xash_root", type=Path)
    ap.add_argument("--overlay-root", type=Path, default=Path(__file__).resolve().parent.parent / "xash-overlay")
    args = ap.parse_args()
    root = args.xash_root.resolve()
    if not (root / "wscript").is_file():
        raise SystemExit(f"not a Xash3D FWGS source root: {root}")
    patch_root_wscript(root)
    patch_engine_wscript(root)
    patch_platform_header(root)
    patch_library_suffix(root)
    install_backend(root, args.overlay_root.resolve())
    verify(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
