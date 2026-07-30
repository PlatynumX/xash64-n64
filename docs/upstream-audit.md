# Current Xash upstream audit for r13

r13 intentionally changes only the architecture assumptions needed to create a real
Nintendo 64 target. The package audits current upstream before applying any edit.

Verified assumptions used by r13:

- root Waf has no N64 target option and always includes `filesystem`;
- the actual submodule path is `3rdparty/library_suffix` (underscore);
- engine Waf exposes `--enable-static-binary`;
- Xash's `xshlib` exposes `--static-linking` and literally searches for `ld` and
  `objcopy`, so the build driver routes those names to libdragon cross-binutils;
- engine configure probes pthreads for almost every non-Windows/non-Android target;
- engine build includes POSIX sources for almost every non-Windows/non-DOS target;
- the engine's generic library branch adds POSIX libraries such as pthread/socket/dl;
- `platform.h` has explicit Switch/Vita/DOS/Windows/Linux dispatch, but no N64 dispatch;
- library_suffix already recognizes MIPS CPU architecture but has no Nintendo 64 OS identifier;
- Xash already has a low-memory mode, which r13 enables for the 8 MiB bring-up.

The CI audit runs against a freshly cloned recursive upstream before the source
integration step. If any audited block drifts, or upstream grows its own
`engine/platform/n64`, r13 stops instead of silently mutating unfamiliar source.
