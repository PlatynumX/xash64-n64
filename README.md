# xash64-n64 r13 — capture the first real Waf/N64 configure failure

r12 finally crossed the source-integration boundary and reached Xash3D FWGS's
real Waf configure step with libdragon's `mips64-elf-gcc/g++` toolchain.

The observed r12 frontier was:

```text
Checking for c flags '-MMD'       : yes
Checking for cxx flags '-MMD'     : yes
Checking for program 'strip'      : /n64_toolchain/bin/mips64-elf-strip
Checking for required C flags     : no
The configuration failed
(complete log in .../build/config.log)
```

r13 deliberately does **not guess at the compiler/linker fix**. Its job is to
preserve the exact Waf `build/config.log`, the configure test directories when
available, and the patched Waf source so the next source change is driven by the
actual command and stderr that failed.

## Important note about `Target OS : linux`

Waf's compiler loader prints its compiler-derived target information while
`compiler_c` / `compiler_cxx` are loading. Our N64 override happens immediately
after that loader returns. r13 therefore prints an explicit later line:

```text
Effective N64 target override : os=n64 cpu=mips binfmt=elf
```

That tells us what Xash is actually using after `--n64` handling instead of
inferring it from the earlier compiler-loader message.

## r13 target

```text
pinned Xash source
  -> guarded N64 integration
  -> libdragon mips64-elf toolchain
  -> Waf configure
  -> preserve exact required-C-flags failure
  -> next revision fixes evidence, not guesses
```

No renderer or HLSDK gameplay code is added in r13. The successful Uplink data
path from r8 remains unchanged:

```text
SD:/xash/valve/pak0.PAK
```

## Diagnostics always uploaded

The GitHub Actions artifact is `xash64-n64-r13`. In addition to the existing
source diff/toolchain files, r13 captures:

```text
xash-r13-configure.log
xash-r13-waf-config.log
xash-r13-conf-checks.tar.gz       # when Waf leaves .conf_check_* dirs
xash-r13-patched-wscript.txt
xash-r13-patched-engine-wscript.txt
```

`xash-r13-waf-config.log` is copied twice defensively: once inside the libdragon
container immediately after configure, and again from the bind-mounted checkout
in the workflow's `if: always()` diagnostics step.

If configure succeeds, r13 continues to the real engine compile exactly as r12
did and preserves the first compiler/linker frontier.

## Host validation

Run:

```sh
./tests/host-check.sh
```

It checks Python syntax, all shell syntax, the consolidated source-integration
fixture, the library_suffix regressions, Uplink/PAK preparation, N64 backend
`-Wall -Wextra -Werror`, config-log capture guards, exact pinned upstream SHAs,
and `git diff --cached --check` over the package.
