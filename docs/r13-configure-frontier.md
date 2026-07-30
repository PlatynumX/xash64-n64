# r13 first real N64 configure frontier

The r13 artifact captured the first failure produced by the actual libdragon
MIPS toolchain rather than by the integration scripts.

Effective target after the custom override:

```text
os=n64 cpu=mips binfmt=elf
```

Representative failing Waf link command:

```text
mips64-elf-gcc
  -mabi=o64
  -g
  -L/n64_toolchain/mips64-elf/lib
  -Wl,-T,n64.ld
  -Wl,--gc-sections
  -Wl,--wrap=__do_global_ctors
  test.c.o
  -o testprog
  -ldragon
  -lm
  -ldragonsys
```

The command did not contain `-lc`. Linker errors then included unresolved
`strlen`, `fprintf`, `malloc`, `_impure_ptr`, `__errno`, and `abort` references
from libdragon/libdragonsys.

The pinned libdragon build rules explicitly put `-lc` on normal N64 ELF link
commands. r14 mirrors that contract instead of skipping Waf's probe.
