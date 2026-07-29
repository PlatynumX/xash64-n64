# xash64-n64 r9 — real Xash3D engine bring-up

r9 is the point where the project stops being an N64 data-path probe and starts
cross-compiling **current Xash3D FWGS itself** for Nintendo 64/libdragon.

The Uplink asset-prep path from r8 is preserved, but r9's main job is now the
engine build.

## r9 target

```text
libdragon boot
  -> N64 becomes a first-class Xash platform (not Linux/POSIX)
  -> real Xash engine core starts
  -> mount SummerCart SD as sd:/
  -> chdir to sd:/xash
  -> Xash filesystem sees valve/pak0.PAK
  -> stop at the first real engine/game-library frontier
```

This is deliberately a **headless/dedicated engine-core bring-up** first. It does
not claim to render Uplink yet and it does not include HLSDK-portable in the ROM
yet. Getting the unmodified Xash core through the MIPS compiler and into its own
filesystem startup gives us a clean, useful frontier before renderer/client work.

## Why the build integration is structured this way

Current Xash builds platform sources from `engine/platform/<DEST_OS>` but also
adds `engine/platform/posix` for almost every non-Windows/non-DOS target and runs
a pthread probe for almost every non-Windows/non-Android target. N64 is therefore
made an explicit exception rather than pretending to be Linux.

r9 also does **not** patch `scripts/waifulib/xcompile.py`. The N64 build instead
supplies libdragon's `mips64-elf-gcc/g++` explicitly and sets the Waf target to
`n64` in the normal root `wscript`. Current Xash's static-link helper separately
looks up programs literally named `ld` and `objcopy`; r9 puts temporary wrappers
for libdragon's `mips64-elf-ld` and `mips64-elf-objcopy` first in `PATH` so Waf
cannot accidentally use the host binutils.

The integration is one consolidated source pass with audited unique blocks. It
aborts on upstream drift and never stacks r9 on top of an already-mutated tree.
CI saves the resulting source diff for inspection.

## N64 runtime backend

`xash-overlay/engine/platform/n64/sys_n64.c` currently implements:

- libdragon timers;
- SummerCart/SC64 USB logging through stderr;
- emulator debug logging;
- flashcart SD mounting at `sd:/`;
- mandatory 8 MiB Expansion Pak check;
- `sd:/xash` as Xash's working/base directory;
- N64 platform init/shutdown;
- safe stubs for unsupported shell/message/status operations.

Expected SD tree is unchanged from the successful r8 preparation:

```text
SD:/
└── xash/
    └── valve/
        └── pak0.PAK
```

Your r8 run already verified the three Uplink maps inside that PAK as BSP v30.

## Build with GitHub Actions

Upload this package as the root of a GitHub repository and run:

```text
Actions -> Build xash64-n64 r9 engine bring-up -> Run workflow
```

CI clones Xash3D FWGS recursively (including `3rdparty/library_suffix`), records
the exact Xash/HLSDK/libdragon SHAs, builds current libdragon, audits the exact
source assumptions, applies the guarded N64 source integration, then runs:

```sh
./waf configure -T debug \
  --n64 \
  --dedicated \
  --enable-static-binary \
  --static-linking=filesystem_stdio \
  --enable-bundled-deps \
  --low-memory-mode=1 \
  --disable-rpath \
  --disable-werror

./waf build -j2 -v
```

The artifact is always named:

```text
xash64-n64-r9
```

Even a failed cross-build uploads `out/`, including:

```text
upstream-revisions.txt
upstream-audit.txt
source-integration.log
xash-r9-configure.log
xash-r9-build.log
xash-r9-source.diff
library-suffix-r9-source.diff
toolchain-version.txt
tool-selection.txt
```

If the engine links successfully it additionally contains:

```text
xash64-n64-r9.elf
xash64-n64-r9.z64
rom-sha256.txt
rom-packaging.log
```

That means the next revision is driven by the **actual first compiler/linker
failure**, not a guessed API mismatch.

## Uplink preparation remains available

The verified r8 route is still included:

```sh
./scripts/prepare-uplink.sh --download "$HOME/xash64-uplink-sd" --force
```

It downloads/verifies the original demo installer, extracts its Wise payload,
finds the Uplink game root, verifies `hldemo1/2/3` inside the PAK, and copies the
**whole game-data tree** to `xash/valve`.

## Host validation

Run:

```sh
./tests/host-check.sh
```

It checks:

- Python compilation;
- Bash syntax;
- the consolidated r9 source-integration regression fixture;
- the existing synthetic Uplink installer/PAK tests;
- `sys_n64.c` with GCC `-Wall -Wextra -Werror` against mocked APIs;
- `git diff --cached --check` over the complete package.

The actual MIPS/libdragon/Xash build cannot be performed in this local execution
environment because the N64 cross-toolchain is not installed here. GitHub Actions
is therefore the first real cross-compile gate, and its logs are deliberately
preserved whether it succeeds or fails.

## After r9

Once the headless core links and boots, the order is:

1. prove Xash's own filesystem opens `valve/pak0.PAK` on SummerCart;
2. cross-compile/link the Uplink-compatible HLSDK server/client code;
3. add N64 controller input;
4. bring up a renderer, initially targeting 320x240 and libdragon's N64 graphics stack;
5. load `hldemo1` and spawn the player;
6. attack the 8 MiB memory budget from real allocation data.
