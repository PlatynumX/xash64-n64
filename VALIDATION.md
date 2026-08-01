# r16 validation

## Evidence from the r15 GitHub Actions artifact

- consolidated source integration completed
- effective target was `os=n64 cpu=mips binfmt=elf`
- required C flags probe passed
- required C++ flags probe passed
- GNU ld archive grouping fixed the prior libc/libdragon dependency cycle
- large-file probe compiled with the real libdragon MIPS compiler and found
  `sizeof(off_t) < 8`
- retrying with `_FILE_OFFSET_BITS=64` produced the same result
- configure stopped only because Xash treats lack of large-file support as
  fatal for platforms without an explicit exception

## r16 correction

- preserve the pinned toolchain, flags, linker script, and archive group
- preserve all mandatory compiler/linker checks
- extend Xash's existing no-large-file platform branch from PSVita to
  `['psvita', 'n64']`
- keep normal 32-bit `off_t`; do not introduce a fake ABI or seek wrapper
- continue automatically into source compilation when configure succeeds

## Local checks

- Python syntax compilation for scripts/tests
- Bash syntax for all shell scripts
- guarded r16 source-integration fixture
- exact N64 large-file exception regression
- large-file probe remains enabled for non-N64 targets
- circular static-archive regression
- Uplink loose/PAK preparation regression
- N64 backend `-Wall -Wextra -Werror` syntax check
- pinned upstream SHA guards
- Waf diagnostics capture guards
- workflow YAML parse
- package `git diff --cached --check`
- ZIP integrity

## Not locally available

- libdragon's actual MIPS cross-toolchain
- live build of the pinned full Xash source tree
- actual N64 ELF/ROM link

The GitHub Actions run is the cross-compile gate.
