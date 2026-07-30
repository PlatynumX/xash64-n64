# xash64-n64 r14 — fix the first real libdragon/Waf link failure

r13 finally captured the exact N64 configure failure instead of a patcher error.

The failing Waf link command already had the pinned libdragon linker script and
libraries:

```text
mips64-elf-gcc ... -T n64.ld ... test.o ... -ldragon -lm -ldragonsys
```

but it omitted newlib libc. The result was a large set of unresolved standard-C
symbols pulled in by libdragon, including `strlen`, `fprintf`, `malloc`,
`_impure_ptr`, `__errno`, and `abort`.

The pinned libdragon `n64.mk` used by this project explicitly links N64 ELFs
with `-lc` before the normal libdragon link flags. r14 makes that one
evidence-driven correction:

```text
-lc -ldragon -lm -ldragonsys
```

No renderer, HLSDK gameplay code, or speculative compatibility patches are
added in this revision.

## r14 target

```text
pinned Xash source
  -> guarded N64 integration
  -> libdragon mips64-elf toolchain
  -> Waf configure
  -> newlib/libdragon link probes succeed
  -> first real Xash compile/link frontier
```

The successful Uplink data preparation from r8 remains unchanged:

```text
SD:/xash/valve/pak0.PAK
```

## Why `Target OS : linux` is not the failure

Waf's compiler loader reports the compiler-derived target before the custom
N64 override is applied. The r13 artifact also recorded the later effective
target as:

```text
Effective N64 target override : os=n64 cpu=mips binfmt=elf
```

The actual fatal error occurred during a link probe, not target dispatch.

## Diagnostics

The GitHub Actions artifact is `xash64-n64-r14`. It always preserves:

```text
xash-r14-configure.log
xash-r14-waf-config.log
xash-r14-conf-checks.tar.gz       # when Waf leaves configure-test dirs
xash-r14-patched-wscript.txt
xash-r14-patched-engine-wscript.txt
xash-r14-source.diff
library-suffix-r14-source.diff
tool-selection.txt
toolchain-version.txt
upstream-revisions.txt
```

If configure succeeds, the workflow continues directly into `./waf build -j2
-v` and preserves that first actual compiler/linker failure.

## Host validation

Run:

```sh
./tests/host-check.sh
```

The local suite checks Python and shell syntax, the consolidated source
integration, the exact `-lc -ldragon -lm -ldragonsys` ordering, library_suffix
regressions, Uplink/PAK preparation, the N64 backend under
`-Wall -Wextra -Werror`, pinned upstream SHA guards, diagnostic capture, and
`git diff --cached --check`.
