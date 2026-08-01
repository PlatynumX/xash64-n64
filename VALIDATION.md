# r15 validation

Evidence from the r14 GitHub Actions artifact:

- source integration completed: PASS
- effective Xash target after override: `os=n64 cpu=mips binfmt=elf`
- Waf reached the real required-C-flags link probe
- the exact command contained `-lc -ldragon -lm -ldragonsys`
- the linker still reported unresolved libc/newlib symbols introduced by
  `libdragon.a` and `libdragonsys.a`
- r14 therefore disproved the simpler diagnosis that libc was merely absent
- build stopped before Xash source compilation because the static archives
  were not rescanned after new undefined references appeared

r15 correction:

- replace the one-pass N64 library sequence with:
  `-Wl,--start-group -lc -ldragon -lm -ldragonsys -Wl,--end-group`
- preserve all platform/source changes from r14 unchanged
- do not bypass Xash's mandatory C or C++ link probes
- preserve full Waf `build/config.log` and first compile/link diagnostics

Validated locally before packaging:

- Python compile for all Python scripts/tests: PASS
- Bash syntax for every shell script: PASS
- r15 source-integration synthetic regression: PASS
- exact GNU ld start/end-group regression: PASS
- real circular static-archive host link: ungrouped FAIL / grouped PASS
- effective N64 target diagnostic insertion: PASS
- PSP/POSIX adjacency regression: PASS
- library_suffix enum dispatch regression: PASS
- Uplink preparation / PAK regression: PASS
- N64 backend `gcc -std=gnu17 -Wall -Wextra -Werror -fsyntax-only`: PASS
- static-link route guards: PASS
- libdragon cross `ld`/`objcopy` routing guards: PASS
- Waf `build/config.log` capture guards in build script + workflow: PASS
- exact pinned Xash/HLSDK/libdragon SHA guards: PASS
- no stale `3rdparty/library-suffix` path: PASS
- complete-package `git diff --cached --check`: PASS

Not locally available:

- libdragon's actual MIPS cross-toolchain in this execution environment
- a live build of the pinned upstream Xash source
- actual N64 ELF/ROM link

The next GitHub Actions run tests this exact archive-group correction and, if
configure passes, advances automatically to the first Xash source compiler
frontier.
