#!/usr/bin/env bash
set -euo pipefail

ELF=${1:?usage: package-xash-rom.sh /path/to/xash.elf [output.z64]}
OUT=${2:-xash64-n64-r11.z64}
: "${N64_INST:?N64_INST must point to the libdragon toolchain root}"

BIN="$N64_INST/bin"
TRIP="$BIN/mips64-elf-"
for tool in n64sym n64elfcompress n64tool; do
    [[ -x "$BIN/$tool" ]] || { echo "ERROR: missing $BIN/$tool" >&2; exit 1; }
done
[[ -x "${TRIP}strip" ]] || { echo "ERROR: missing ${TRIP}strip" >&2; exit 1; }
[[ -f "$ELF" ]] || { echo "ERROR: ELF not found: $ELF" >&2; exit 1; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cp "$ELF" "$WORK/xash.elf"
"$BIN/n64sym" "$WORK/xash.elf" "$WORK/xash.sym"
cp "$WORK/xash.elf" "$WORK/xash.stripped"
"${TRIP}strip" -s "$WORK/xash.stripped"
"$BIN/n64elfcompress" -o "$WORK" -c 1 "$WORK/xash.stripped"
rm -f "$OUT"
"$BIN/n64tool" --title "Xash64 Uplink r11" --toc --output "$OUT" \
    --align 256 "$WORK/xash.stripped" --align 8 "$WORK/xash.sym" --align 8
printf 'ROM: %s\n' "$OUT"
sha256sum "$OUT"
