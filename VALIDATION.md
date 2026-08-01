# r17 validation

## Evidence from the r16 GitHub Actions artifact

- effective target: `os=n64 cpu=mips binfmt=elf`
- required C and C++ flag/link probes passed
- large-file capability was accepted as intended for N64
- Waf configure finished successfully
- the real build started with 222 tasks
- the first source error occurred in `public/miniz.c`
- exact failure: implicit declaration of `utime()` in
  `mz_zip_set_file_times()`

## r17 correction

- preserve every r16 compiler, linker, platform, filesystem, and low-memory
  change
- patch the exact audited `mz_zip_set_file_times()` function once
- keep the upstream `utime()` implementation on non-N64 platforms
- on N64 only, skip writable timestamp restoration and return success
- do not weaken global warning policy or suppress implicit declarations
- preserve pristine `public/miniz.c` in the GitHub artifact

## Local checks

- Python syntax compilation for scripts/tests
- Bash syntax for all shell scripts
- guarded r17 source-integration fixture
- N64/non-N64 miniz timestamp-branch compile regression
- exact N64 32-bit `off_t` exception regression
- circular static-archive regression
- Uplink loose/PAK preparation regression
- N64 backend `-Wall -Wextra -Werror` syntax check
- pinned upstream SHA guards
- Waf diagnostics capture guards
- package `git diff --cached --check`
- ZIP integrity

## Cross-build boundary

The complete pinned Xash/libdragon MIPS build runs in GitHub Actions. The next
artifact is expected either to contain a ROM or the next exact source/compiler
frontier after `public/miniz.c`.
