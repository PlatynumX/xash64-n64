# r8: Uplink extraction and WON PAK detection

The r7 Termux run proved that the extraction layer itself now works:

- the cached `hluplink.exe` passed its known MD5;
- REWise 0.3.1 launched with a writable Termux temporary directory;
- REWise reported successful extraction of the Wise installer;
- the extracted tree contained `MAINDIR/hldemo.exe` and other recovered files.

The remaining r7 failure was our data-root detector. It only recognized Uplink when
`maps/hldemo1.bsp`, `hldemo2.bsp`, and `hldemo3.bsp` existed as loose files. That is
too narrow for WON-era Half-Life layouts, where game assets are commonly stored in
`valve/pak0.pak`.

r8 therefore parses Half-Life/Quake PACK archives directly. A candidate game root is
accepted when either:

1. all three Uplink BSPs exist loose under `maps/`; or
2. a `.pak` in the game root contains all three entries under `maps/`.

For PAK-backed data, r8 validates each embedded BSP header as version 30 without
extracting or duplicating the map files. The complete game root is copied unchanged
to `SDROOT/xash/valve`, preserving the format Xash expects.

The N64 probe was updated in the same revision: it first checks loose maps and then
falls back to `sd:/xash/valve/pak0.pak`, reading and benchmarking `hldemo1.bsp`
directly from its PAK offset.

If neither layout is found, r8 preserves an extracted-file inventory at:

    ~/.cache/xash64-n64/uplink-extracted-inventory.txt

That gives the next diagnostic the exact extracted tree instead of another blind
extractor guess.
