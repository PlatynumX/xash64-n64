# r9 validation

Validated locally before packaging:

- `python3 -m py_compile`: PASS
- Bash syntax for every shell script: PASS
- r9 source-integration synthetic regression: PASS
- Uplink preparation synthetic regression: PASS
- N64 backend `gcc -std=gnu17 -Wall -Wextra -Werror -fsyntax-only`: PASS
- static-link route guard (`--enable-static-binary` + `--static-linking=filesystem_stdio`): PASS
- libdragon cross `ld`/`objcopy` wrapper routing guard: PASS
- no stale `3rdparty/library-suffix` path in scripts/tests/workflow: PASS
- complete-package `git diff --cached --check`: PASS

Not locally available:

- libdragon MIPS cross-toolchain
- full current Xash3D FWGS source checkout over Git in this execution environment
- actual N64 ELF/ROM link

GitHub Actions is configured to perform those missing checks against freshly cloned
upstream and to upload diagnostics even when the first real N64 compile/link frontier
fails.
