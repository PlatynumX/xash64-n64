# xash64-n64 r15 — fix the real static-archive dependency cycle

r14 reached Xash's real N64 Waf configure step, but the required-C-flags link
probe still failed. The r14 artifact proves that `-lc` was present this time:

```text
... test.o ... -lc -ldragon -lm -ldragonsys
```

The remaining unresolved symbols were introduced by archives *after* newlib
libc had already been scanned. Libdragon and libdragonsys require libc/newlib,
and newlib can in turn require libdragonsys system calls. A one-pass static
archive order cannot reliably resolve that cycle.

r15 keeps the N64 runtime archives in one GNU ld group:

```text
-Wl,--start-group -lc -ldragon -lm -ldragonsys -Wl,--end-group
```

GNU ld repeatedly searches archives inside a group until no new undefined
references are created. This directly addresses the link command captured in
the r14 artifact; it does not skip or weaken Xash's configure checks.

No renderer, HLSDK gameplay code, or speculative source compatibility patches
are added in this revision.

## r15 target

```text
pinned Xash source
  -> guarded N64 integration
  -> libdragon mips64-elf toolchain
  -> Waf required C/C++ link probes pass
  -> first actual Xash source compile frontier
```

The successful Uplink data preparation remains unchanged:

```text
SD:/xash/valve/pak0.PAK
```

## Evidence from r14

The artifact's exact required-C-flags command was:

```text
mips64-elf-gcc
  -mabi=o64
  -L/n64_toolchain/mips64-elf/lib
  -Wl,-T,n64.ld
  test.o
  -lc
  -ldragon
  -lm
  -ldragonsys
```

The linker then reported unresolved `strstr`, `fprintf`, `_impure_ptr`,
`malloc`, `__errno`, `abort`, and related libc/newlib references from
`libdragon.a` and `libdragonsys.a`. That proves r14's single leading `-lc` was
scanned too early; libc was no longer absent.

## Diagnostics

The GitHub Actions artifact is `xash64-n64-r15`. It always preserves:

```text
xash-r15-configure.log
xash-r15-waf-config.log
xash-r15-conf-checks.tar.gz       # when Waf leaves configure-test dirs
xash-r15-patched-wscript.txt
xash-r15-patched-engine-wscript.txt
xash-r15-source.diff
library-suffix-r15-source.diff
tool-selection.txt
toolchain-version.txt
upstream-revisions.txt
```

If configure succeeds, the workflow continues directly into `./waf build -j2
-v` and preserves the first actual source compiler/linker failure.

## Host validation

Run:

```sh
./tests/host-check.sh
```

The local suite checks Python and shell syntax, consolidated source
integration, the exact N64 GNU ld group, a real host-side circular static
archive regression, library_suffix regressions, Uplink/PAK preparation, the
N64 backend under `-Wall -Wextra -Werror`, pinned upstream SHA guards,
diagnostic capture, and `git diff --cached --check`.
