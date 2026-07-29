# r10 validation

Validated locally before packaging:

- `python3 -m py_compile`: PASS
- Bash syntax for every shell script: PASS
- r10 source-integration synthetic regression: PASS
- shifted-enum regression (`PLATFORM_PSP` and `ARCHITECTURE_MIPS` not hard-coded): PASS
- next-free `PLATFORM_N64` allocation regression: PASS
- Uplink preparation synthetic regression: PASS
- N64 backend `gcc -std=gnu17 -Wall -Wextra -Werror -fsyntax-only`: PASS
- static-link route guard (`--enable-static-binary` + `--static-linking=filesystem_stdio`): PASS
- libdragon cross `ld`/`objcopy` wrapper routing guard: PASS
- r9-reported Xash/HLSDK/libdragon SHAs pinned in r10 workflow: PASS
- workflow YAML parse: PASS
- no stale `3rdparty/library-suffix` path in scripts/tests/workflow: PASS
- complete-package `git diff --cached --check`: PASS
- final ZIP integrity test: PASS

The uploaded r9 CI artifact was inspected before r10. It stopped in the source audit
before `apply-n64-port.py`, Waf configure, or MIPS compilation. The only reported
audit failures were hard-coded numeric expectations for `PLATFORM_PSP` and
`ARCHITECTURE_MIPS`; all structural anchors needed by the N64 integration passed.

Not locally available:

- libdragon MIPS cross-toolchain
- the exact pinned Xash checkout over Git in this execution environment
- actual N64 ELF/ROM link

GitHub Actions performs those missing checks against the exact upstream revisions
recorded by the r9 artifact and uploads diagnostics at the next real frontier.
