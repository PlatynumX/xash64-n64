#!/usr/bin/env python3
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory(prefix="xash64-r17-test-") as td:
    x = Path(td) / "xash"
    (x / "engine/platform").mkdir(parents=True)
    (x / "public").mkdir(parents=True)
    (x / "3rdparty/library_suffix/include").mkdir(parents=True)

    (x / "wscript").write_text("""\\
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
\tconf.define_cond('XASH_ALL_SERVERS', conf.options.ALL_SERVERS)

\t# check if we can use C99 stdint
\tconf.define('STDINT_H', 'stdint.h')
\t# check if we can use alloca.h or malloc.h
\tif conf.check_cc(header_name='alloca.h', mandatory=False):
\t\tpass

\tif conf.env.DEST_OS == 'nswitch':
\t\tconf.check_cfg(package='solder', args='--cflags --libs', uselib_store='SOLDER')
\t\tconf.check_cc(lib='m')
\telif conf.env.DEST_OS == 'psvita':
\t\tconf.check_cc(lib='vrtld')
\t\tconf.check_cc(lib='m')
\telif conf.env.DEST_OS == 'android':
\t\tconf.check_cc(lib='dl')
\t\tconf.check_cc(lib='log')
\telif conf.env.DEST_OS == 'win32':
\t\tpass
\telse:
\t\tconf.check_cc(lib='dl', mandatory = False)
\t\tconf.check_cc(lib='m')

\t# set _FILE_OFFSET_BITS=64 for filesystems with 64-bit inodes
\t# must be set globally as it changes ABI
\tif conf.env.DEST_OS == 'android' and conf.env.DEST_SIZEOF_VOID_P == 4:
\t\t# Android in 32-bit mode don't have good enough large file support
\t\tpass
\telif conf.env.DEST_OS == 'psvita':
\t\t# PSVita don't have large file support at all
\t\tpass
\telse:
\t\t# try to guess how to support large files
\t\tconf.check_large_file(compiler = 'c', execute = False)
""", encoding="utf-8")


    (x / "public/miniz.c").write_text("""\
static mz_bool mz_zip_set_file_times(const char *pFilename, MZ_TIME_T access_time, MZ_TIME_T modified_time)
{
    struct utimbuf t;

    memset(&t, 0, sizeof(t));
    t.actime = access_time;
    t.modtime = modified_time;

    return !utime(pFilename, &t);
}
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
#elif defined __future_console__
 #define XASH_FUTURE_TEST 1
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
#elif XASH_FUTURE_TEST
 #define XASH_PLATFORM PLATFORM_FUTURE_TEST
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
    root_text = (x / "wscript").read_text()
    assert "DEST_OS = 'n64'" in root_text
    assert "Effective N64 target override" in root_text
    assert "'-Wl,--start-group', '-lc', '-ldragon', '-lm', '-ldragonsys', '-Wl,--end-group'" in root_text
    assert "if conf.env.DEST_OS == 'n64':" in root_text
    assert "elif conf.env.DEST_OS == 'nswitch':\n\t\tconf.check_cfg(package='solder'" in root_text
    assert "elif conf.env.DEST_OS in ['psvita', 'n64']:" in root_text
    assert "libdragon/newlib N64 don't have 64-bit off_t support" in root_text
    assert root_text.count("conf.check_large_file(compiler = 'c', execute = False)") == 1
    miniz_text = (x / "public/miniz.c").read_text()
    assert "#if defined(N64) || defined(__N64__)" in miniz_text
    assert "libdragon filesystems do not provide writable file timestamps" in miniz_text
    assert miniz_text.count("return !utime(pFilename, &t);") == 1
    engine_text = (x / "engine/wscript").read_text()
    assert "['win32', 'android', 'n64']" in engine_text
    assert "['win32', 'dos', 'n64']" in engine_text
    assert "DEST_OS == 'n64'" in engine_text
    build_text = (x / "3rdparty/library_suffix/include/build.h").read_text()
    assert "XASH_N64" in build_text
    assert "#elif defined __future_console__\n #define XASH_FUTURE_TEST 1" in build_text
    assert build_text.index("#elif defined N64 || defined __N64__") < build_text.index("#else // POSIX compatible")
    enum_text = (x / "3rdparty/library_suffix/include/buildenums.h").read_text()
    assert "#define PLATFORM_N64 24" in enum_text
    assert "#define XASH_PLATFORM PLATFORM_N64" in enum_text
    assert "#elif XASH_FUTURE_TEST\n #define XASH_PLATFORM PLATFORM_FUTURE_TEST" in enum_text
    assert (x / "engine/platform/n64/sys_n64.c").is_file()

print("test-r17-integration: PASS")
