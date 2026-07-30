# r13 validation

Validated locally before packaging:

- Python compile for all Python scripts/tests: PASS
- Bash syntax for every shell script: PASS
- r13 source-integration synthetic regression: PASS
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

- libdragon MIPS cross-toolchain
- the pinned upstream Xash checkout over Git
- the real r12 `build/config.log` from the user's GitHub Actions container
- actual N64 ELF/ROM link

Therefore r13 intentionally captures the missing Waf diagnostic instead of
changing the required-C-flags path speculatively.
