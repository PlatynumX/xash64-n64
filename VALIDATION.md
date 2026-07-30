# r14 validation

Evidence from the r13 GitHub Actions artifact:

- source integration completed: PASS
- effective Xash target after override: `os=n64 cpu=mips binfmt=elf`
- libdragon MIPS C and C++ compilers accepted the N64 compile flags
- Waf reached real link probes
- failing link omitted `-lc`
- linker reported unresolved newlib/libc symbols from `libdragon.a` and
  `libdragonsys.a`
- build stopped before Xash compilation because the mandatory required-C-flags
  probe could not link

r14 correction:

- add explicit libc to the N64 link set as
  `-lc -ldragon -lm -ldragonsys`
- preserve all r13 source/platform changes unchanged
- preserve full Waf `build/config.log` and first compile/link diagnostics

Validated locally before packaging:

- Python compile for all Python scripts/tests: PASS
- Bash syntax for every shell script: PASS
- r14 source-integration synthetic regression: PASS
- exact libc/libdragon link-order regression: PASS
- effective N64 target diagnostic insertion: PASS
- r11 PSP/POSIX adjacency regression: PASS
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
- a live Git clone of the pinned upstream sources
- actual N64 ELF/ROM link

The next GitHub Actions run therefore tests this exact linker correction and,
if configure passes, advances automatically to the first Xash source compiler
frontier.
