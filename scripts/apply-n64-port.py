#!/usr/bin/env python3
"""Apply the consolidated r10 Nintendo 64 source changes to pristine Xash3D FWGS.

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

    replace_once(
        p,
        "\tconf.env.GAMEDIR = conf.options.GAMEDIR\n\tconf.define('XASH_GAMEDIR', conf.options.GAMEDIR)\n\tif conf.env.DEST_OS == 'nswitch':\n",
        "\tconf.env.GAMEDIR = conf.options.GAMEDIR\n\tconf.define('XASH_GAMEDIR', conf.options.GAMEDIR)\n"
        "\tif conf.env.DEST_OS == 'n64':\n"
        "\t\t# libdragon/newlib and the final link line are provided by the N64 target.\n"
        "\t\tpass\n"
        "\telif conf.env.DEST_OS == 'nswitch':\n",
        "skip host library probes",
    )

    replace_once(
        p,
        "\telif conf.env.DEST_OS == 'psvita':\n\t\t# PSVita don't have large file support at all\n\t\tpass\n\telse:\n\t\t# try to guess how to support large files\n",
        "\telif conf.env.DEST_OS in ['psvita', 'n64']:\n"
        "\t\t# Do not run a host-style large-file ABI probe for console libc targets.\n"
        "\t\tpass\n\telse:\n\t\t# try to guess how to support large files\n",
        "skip host large-file probe",
    )


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


def patch_library_suffix(root: Path) -> None:
    d = root / "3rdparty/library_suffix/include"
    build_h = d / "build.h"
    enums_h = d / "buildenums.h"
    if not build_h.is_file() or not enums_h.is_file():
        raise SystemExit("library_suffix submodule missing: clone Xash with --recursive")

    replace_once(build_h, "#undef XASH_NSWITCH\n", "#undef XASH_NSWITCH\n#undef XASH_N64\n", "declare XASH_N64")
    replace_once(
        build_h,
        "#elif defined __psp__\n #define XASH_PSP 1\n#else // POSIX compatible\n",
        "#elif defined __psp__\n #define XASH_PSP 1\n"
        "#elif defined N64 || defined __N64__\n #define XASH_N64 1\n"
        "#else // POSIX compatible\n",
        "make N64 a first-class non-POSIX platform",
    )
    # Do not hard-code library-suffix's numeric enum table. r9 proved that
    # numeric values can drift independently of the source structure. Parse the
    # pristine table, allocate the next free platform ID, then insert N64 before
    # the XASH_PLATFORM dispatch block.
    enum_text = enums_h.read_text(encoding="utf-8")
    if re.search(r"(?m)^\s*#\s*define\s+PLATFORM_N64\b", enum_text):
        raise SystemExit("library_suffix already defines PLATFORM_N64; re-audit instead of overwriting it")
    platform_defs = [
        (m.group(1), int(m.group(2)))
        for m in re.finditer(r"(?m)^\s*#\s*define\s+(PLATFORM_[A-Z0-9_]+)\s+([0-9]+)\s*(?://.*)?$", enum_text)
    ]
    if not platform_defs:
        raise SystemExit(f"{enums_h}: no numeric PLATFORM_* defines found")
    if not any(name == "PLATFORM_PSP" for name, _ in platform_defs):
        raise SystemExit(f"{enums_h}: PLATFORM_PSP anchor missing")
    n64_platform_id = max(value for _, value in platform_defs) + 1
    dispatch_anchor = "#if XASH_WIN32\n"
    if enum_text.count(dispatch_anchor) != 1:
        raise SystemExit(f"{enums_h}: expected exactly one XASH platform dispatch anchor")
    enum_text = enum_text.replace(
        dispatch_anchor,
        f"#define PLATFORM_N64 {n64_platform_id}\n\n{dispatch_anchor}",
        1,
    )
    enums_h.write_text(enum_text, encoding="utf-8")
    print(f"patched {enums_h}: add N64 platform enum as {n64_platform_id}")

    replace_once(
        enums_h,
        "#elif XASH_PSP\n #define XASH_PLATFORM PLATFORM_PSP\n#else\n",
        "#elif XASH_PSP\n #define XASH_PLATFORM PLATFORM_PSP\n"
        "#elif XASH_N64\n #define XASH_PLATFORM PLATFORM_N64\n"
        "#else\n",
        "map N64 platform enum",
    )


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
    print("r10 N64 source integration verification: PASS")


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
