# r14 static-archive configure frontier

r14 added an explicit leading `-lc`. The GitHub Actions artifact confirmed it
was present in the failing required-C-flags command:

```text
mips64-elf-gcc ... test.o ... -lc -ldragon -lm -ldragonsys
```

The link still failed with libc/newlib symbols referenced from archives that
were scanned later, including:

```text
strstr
fprintf
_impure_ptr
malloc
free
__errno
abort
```

This changes the diagnosis. Libc is not missing; the archives have circular or
reverse-order dependencies that a single-pass static link does not resolve.

r15 groups the N64 runtime archives so GNU ld searches them repeatedly:

```text
-Wl,--start-group -lc -ldragon -lm -ldragonsys -Wl,--end-group
```
