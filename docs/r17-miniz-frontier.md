# r16 → r17 frontier: miniz file timestamps

r16 completed Xash configure and entered the real 222-task N64 build. The first
source error was `public/miniz.c`: its extraction helper calls `utime()` to copy
archive timestamps to an extracted file. The libdragon/newlib target does not
expose a usable `utime()` declaration for this build.

r17 keeps the upstream implementation on every other platform. On N64 only, the
helper reports success without changing timestamps. This affects post-extraction
metadata, not archive reads, decompression, file contents, PAK access, or map
loading.
