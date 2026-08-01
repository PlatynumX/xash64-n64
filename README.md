# xash64-n64 r16 — accept libdragon's 32-bit `off_t`

r15 successfully passed Xash3D FWGS's mandatory C and C++ compiler/linker
checks. It then stopped at Xash's large-file configure gate.

The r15 artifact proves both large-file tests fail with the pinned libdragon
MIPS toolchain:

```text
sizeof(off_t) >= 8                 : no
-D_FILE_OFFSET_BITS=64             : no
There is no support for large files
```

That is a platform capability result, not a broken compiler command. Xash
already permits PSVita to configure without 64-bit file offsets. r16 gives N64
the same explicit treatment:

```python
elif conf.env.DEST_OS in ['psvita', 'n64']:
    pass
```

This is sufficient for the current Uplink target. Its complete `pak0.PAK` is
79,150,544 bytes, well inside signed 32-bit file-offset range. The PAK remains
intact at:

```text
SD:/xash/valve/pak0.PAK
```

r16 does not redefine `off_t`, fake `_FILE_OFFSET_BITS=64`, or weaken the
mandatory C/C++ probes. It only prevents Xash's generic desktop large-file gate
from rejecting a console target that does not support files above 2 GiB.

## r16 target

```text
configure C/C++ probes pass
  -> accept N64 32-bit off_t
  -> complete Waf configure
  -> enter real Xash source compilation
  -> capture first source/compiler frontier
```

No renderer or HLSDK gameplay code is added in this revision.

## GitHub Actions artifact

The workflow always uploads `xash64-n64-r16`, containing the ROM when one is
produced or the first-frontier diagnostics otherwise:

```text
xash-r16-configure.log
xash-r16-waf-config.log
xash-r16-build.log
xash-r16-conf-checks.tar.gz        # when present
xash-r16-patched-wscript.txt
xash-r16-patched-engine-wscript.txt
xash-r16-source.diff
library-suffix-r16-source.diff
tool-selection.txt
toolchain-version.txt
upstream-revisions.txt
```

## Local validation

```sh
./tests/host-check.sh
```
