#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
XASH=${1:-"$ROOT/upstream/xash3d-fwgs"}
OUT=${2:-"$ROOT/out"}
: "${N64_INST:?N64_INST must point to the libdragon toolchain root}"

TRIP="$N64_INST/bin/mips64-elf-"
for tool in gcc g++ gcc-ar ld objcopy strip objdump; do
    [[ -x "${TRIP}${tool}" ]] || { echo "ERROR: missing ${TRIP}${tool}" >&2; exit 1; }
done

mkdir -p "$OUT"
: > "$OUT/source-integration.log"
: > "$OUT/xash-r9-configure.log"
: > "$OUT/xash-r9-build.log"
: > "$OUT/rom-packaging.log"

# Feed Waf the libdragon compiler directly. We intentionally do not patch
# Xash's xcompile.py or impersonate a Linux/POSIX target.
export CC="${TRIP}gcc"
export CXX="${TRIP}g++"
export AR="${TRIP}gcc-ar"
export LD="${TRIP}ld"
export OBJCOPY="${TRIP}objcopy"
export STRIP="${TRIP}strip"
export OBJDUMP="${TRIP}objdump"

# Xash's current xshlib helper explicitly calls find_program('ld') and
# find_program('objcopy') when --static-linking is active. Put wrappers named
# exactly as requested first in PATH so Waf cannot accidentally select the
# host linker/binutils from the libdragon Docker image.
TOOLWRAP=$(mktemp -d)
cleanup() { rm -rf "$TOOLWRAP"; }
trap cleanup EXIT
ln -s "$LD" "$TOOLWRAP/ld"
ln -s "$OBJCOPY" "$TOOLWRAP/objcopy"
export PATH="$TOOLWRAP:$PATH"

{
    echo "N64_INST=$N64_INST"
    echo "CC=$CC"
    echo "CXX=$CXX"
    echo "AR=$AR"
    echo "LD=$LD"
    echo "OBJCOPY=$OBJCOPY"
    echo "STRIP=$STRIP"
    echo "OBJDUMP=$OBJDUMP"
    echo "PATH ld=$(command -v ld)"
    echo "PATH objcopy=$(command -v objcopy)"
    "$CC" --version | head -n 1
    ld --version | head -n 1
    objcopy --version | head -n 1
} | tee "$OUT/tool-selection.txt"

python3 "$ROOT/scripts/apply-n64-port.py" "$XASH" | tee "$OUT/source-integration.log"

cd "$XASH"
./waf distclean >/dev/null 2>&1 || true
set +e
./waf configure -T debug \
    --n64 \
    --dedicated \
    --enable-static-binary \
    --static-linking=filesystem_stdio \
    --enable-bundled-deps \
    --low-memory-mode=1 \
    --disable-rpath \
    --disable-werror 2>&1 | tee "$OUT/xash-r9-configure.log"
config_rc=${PIPESTATUS[0]}
set -e
if (( config_rc != 0 )); then
    echo "Xash r9 reached a real N64 configure frontier (exit $config_rc)." >&2
    exit "$config_rc"
fi

set +e
./waf build -j2 -v 2>&1 | tee "$OUT/xash-r9-build.log"
build_rc=${PIPESTATUS[0]}
set -e
if (( build_rc != 0 )); then
    echo "Xash r9 reached a real N64 compile/link frontier (exit $build_rc)." >&2
    exit "$build_rc"
fi

ELF=$(find build -type f -name xash -print -quit)
[[ -n "$ELF" && -f "$ELF" ]] || { echo "ERROR: Waf completed but no xash ELF was found" >&2; exit 1; }
cp "$ELF" "$OUT/xash64-n64-r9.elf"
"$ROOT/scripts/package-xash-rom.sh" "$OUT/xash64-n64-r9.elf" "$OUT/xash64-n64-r9.z64" | tee "$OUT/rom-packaging.log"
