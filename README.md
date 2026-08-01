# xash64-n64 r17 — first real Xash source portability fix

r16 completed Xash3D FWGS configuration and entered the real N64 build:

```text
'configure' finished successfully
[  1/222] Processing public/build_vcs.c
...
[  8/222] Processing public/miniz.c
```

The first source failure is now exact and reproducible:

```text
public/miniz.c:3504:17: error: implicit declaration of function 'utime'
```

`miniz` calls `utime()` only after extracting a ZIP member, to copy the
archive's access/modified timestamps onto the output file. The libdragon/newlib
N64 target does not expose a usable `utime()` entry point for this build.

r17 keeps upstream behavior unchanged everywhere else. On N64 only,
`mz_zip_set_file_times()` reports success without changing timestamps:

```c
#if defined(N64) || defined(__N64__)
    (void)pFilename;
    (void)access_time;
    (void)modified_time;
    return MZ_TRUE;
#else
    /* upstream utime() path */
#endif
```

This does **not** change ZIP reads, decompression, extracted bytes, PAK access,
or map loading. It only drops output-file timestamp metadata on N64.

Half-Life/Uplink resources remain external on the SummerCart SD card:

```text
SD:/xash/valve/pak0.PAK
```

No Valve assets are included in this package or the ROM.

## r17 target

```text
complete Waf configure
  -> compile real Xash sources
  -> pass public/miniz.c
  -> capture the next exact N64 compiler/linker frontier
```

## GitHub Actions artifact

The workflow always uploads `xash64-n64-r17`, containing the ROM when one is
produced or first-frontier diagnostics otherwise:

```text
xash-r17-configure.log
xash-r17-waf-config.log
xash-r17-build.log
xash-r17-conf-checks.tar.gz        # when present
xash-r17-patched-wscript.txt
xash-r17-patched-engine-wscript.txt
xash-r17-source.diff
library-suffix-r17-source.diff
miniz.pristine.c
tool-selection.txt
toolchain-version.txt
upstream-revisions.txt
```

## Local validation

```sh
./tests/host-check.sh
```
