#!/usr/bin/env python3
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory(prefix="xash64-r10-test-") as td:
    x = Path(td) / "xash"
    (x / "engine/platform").mkdir(parents=True)
    (x / "3rdparty/library_suffix/include").mkdir(parents=True)

    (x / "wscript").write_text("""\
def options(opt):
\tgrp = opt.add_option_group('Common options')
\tgrp.add_option('-d', '--dedicated', action = 'store_true', dest = 'DEDICATED', default = False,
\t\thelp = 'only build Xash Dedicated Server [default: %(default)s]')

def configure(conf):
\t# Load compilers early
\tconf.load('xshlib xcompile compiler_c compiler_cxx')

\telif conf.env.DEST_OS == 'emscripten':
\t\tconf.options.BUILD_BUNDLED_DEPS = True
\tif conf.options.ENABLE_RPATH and conf.env.DEST_OS not in ['nswitch', 'psvita']:
\t\tpass
\tconf.env.GAMEDIR = conf.options.GAMEDIR
\tconf.define('XASH_GAMEDIR', conf.options.GAMEDIR)
\tif conf.env.DEST_OS == 'nswitch':
\t\tpass
\telif conf.env.DEST_OS == 'psvita':
\t\t# PSVita don't have large file support at all
\t\tpass
\telse:
\t\t# try to guess how to support large files
\t\tpass
""", encoding="utf-8")

    (x / "engine/wscript").write_text("""\
def configure(conf):
\tif not conf.env.DEST_OS in ['win32', 'android']:
\t\tconf.check_pthreads(mode='c')

def build(bld):
\tif bld.env.DEST_OS not in ['win32', 'dos']:
\t\tsource += bld.path.ant_glob('platform/posix/*.c')
\tif bld.env.DEST_OS == 'win32':
\t\tlibs += ['USER32', 'SHELL32', 'GDI32', 'ADVAPI32', 'DBGHELP', 'PSAPI', 'WS2_32']
""", encoding="utf-8")

    (x / "engine/platform/platform.h").write_text("""\
#if XASH_NSWITCH
void NSwitch_Init( void );
void NSwitch_Shutdown( void );
#endif
static inline void Platform_Init( qboolean con_showalways )
{
#if XASH_ANDROID
\tAndroid_Init( );
#elif XASH_NSWITCH
\tNSwitch_Init( );
#endif
}
static inline void Platform_Shutdown( void )
{
#if XASH_NSWITCH
\tNSwitch_Shutdown( );
#endif
}
""", encoding="utf-8")

    (x / "3rdparty/library_suffix/include/build.h").write_text("""\
#undef XASH_NSWITCH
#undef XASH_PSP
#elif defined __psp__
 #define XASH_PSP 1
#else // POSIX compatible
 #define XASH_POSIX 1
#endif
""", encoding="utf-8")
    (x / "3rdparty/library_suffix/include/buildenums.h").write_text("""\
#define PLATFORM_PSP 20
#define PLATFORM_FUTURE_TEST 23
#if XASH_WIN32
 #define XASH_PLATFORM PLATFORM_WIN32
#elif XASH_PSP
 #define XASH_PLATFORM PLATFORM_PSP
#else
 #error
#endif
#define ARCHITECTURE_MIPS 42
#if XASH_MIPS
 #define XASH_ARCHITECTURE ARCHITECTURE_MIPS
#endif
""", encoding="utf-8")

    subprocess.run([
        "python3", str(ROOT / "scripts/apply-n64-port.py"), str(x),
        "--overlay-root", str(ROOT / "xash-overlay")
    ], check=True)

    assert "--n64" in (x / "wscript").read_text()
    assert "DEST_OS = 'n64'" in (x / "wscript").read_text()
    engine_text = (x / "engine/wscript").read_text()
    assert "['win32', 'android', 'n64']" in engine_text
    assert "['win32', 'dos', 'n64']" in engine_text
    assert "DEST_OS == 'n64'" in engine_text
    assert "XASH_N64" in (x / "3rdparty/library_suffix/include/build.h").read_text()
    enum_text = (x / "3rdparty/library_suffix/include/buildenums.h").read_text()
    assert "#define PLATFORM_N64 24" in enum_text
    assert "#define XASH_PLATFORM PLATFORM_N64" in enum_text
    assert (x / "engine/platform/n64/sys_n64.c").is_file()

print("test-r10-integration: PASS")
