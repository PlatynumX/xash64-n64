#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

python3 -m py_compile \
    "$ROOT/scripts/audit-xash-upstream.py" \
    "$ROOT/scripts/apply-n64-port.py" \
    "$ROOT/scripts/prepare-uplink.py" \
    "$ROOT/tests/test-r17-integration.py" \
    "$ROOT/tests/test-prepare-uplink.py"

for script in "$ROOT"/scripts/*.sh "$ROOT"/tests/*.sh; do
    bash -n "$script"
done

python3 "$ROOT/tests/test-r17-integration.py"
python3 "$ROOT/tests/test-prepare-uplink.py"
bash "$ROOT/tests/test-static-archive-group.sh"
bash "$ROOT/tests/test-miniz-n64-time.sh"

gcc -std=gnu17 -Wall -Wextra -Werror -fsyntax-only \
    -I"$ROOT/tests/mock_xash" \
    -I"$ROOT/tests/mock_libdragon" \
    "$ROOT/xash-overlay/engine/platform/n64/sys_n64.c"


# r9 regression: enum values are discovered from pristine library_suffix source,
# never assumed from an old snapshot.
if grep -q '#define PLATFORM_PSP 18' "$ROOT/scripts/audit-xash-upstream.py" "$ROOT/scripts/apply-n64-port.py"; then
    echo "ERROR: stale hard-coded PLATFORM_PSP value remains" >&2
    exit 1
fi
if grep -q '#define ARCHITECTURE_MIPS 4' "$ROOT/scripts/audit-xash-upstream.py"; then
    echo "ERROR: stale hard-coded ARCHITECTURE_MIPS value remains" >&2
    exit 1
fi
grep -q 'max(value for _, _, value in platform_defs) + 1' "$ROOT/scripts/apply-n64-port.py"
grep -q 'ecda80fb9a29d45099a624344456eb3c7d01473d' "$ROOT/.github/workflows/build-r17.yml"
grep -q '35f85a0797324a5ed0c723203e33ab3c1da94fdd' "$ROOT/.github/workflows/build-r17.yml"

# Regression guards for the real current-Xash static-link route.
grep -q -- '--enable-static-binary' "$ROOT/scripts/build-xash-r17.sh"
grep -q -- '--static-linking=filesystem_stdio' "$ROOT/scripts/build-xash-r17.sh"
grep -q 'mips64-elf-' "$ROOT/scripts/build-xash-r17.sh"
grep -q 'TOOLWRAP' "$ROOT/scripts/build-xash-r17.sh"
grep -q 'xash-r17-waf-config.log' "$ROOT/scripts/build-xash-r17.sh"
grep -q "build/config.log" "$ROOT/scripts/build-xash-r17.sh" "$ROOT/.github/workflows/build-r17.yml"
grep -q 'Effective N64 target override' "$ROOT/scripts/apply-n64-port.py"
grep -q -- "'-Wl,--start-group', '-lc', '-ldragon', '-lm', '-ldragonsys', '-Wl,--end-group'" "$ROOT/scripts/apply-n64-port.py"
grep -q 'mutually dependent N64 archives in one GNU ld group' "$ROOT/scripts/apply-n64-port.py"
grep -q "elif conf.env.DEST_OS in \['psvita', 'n64'\]" "$ROOT/scripts/apply-n64-port.py"
grep -q 'accept N64 32-bit off_t like PSVita' "$ROOT/scripts/apply-n64-port.py"
grep -q 'disable unsupported N64 timestamp restoration' "$ROOT/scripts/apply-n64-port.py"
grep -q 'libdragon filesystems do not provide writable file timestamps' "$ROOT/scripts/apply-n64-port.py"
grep -q '3rdparty/library_suffix' "$ROOT/scripts/apply-n64-port.py"
# r11 regression: do not require the PSP branch to be textually adjacent to
# the POSIX fallback. The r17 patcher must locate the fallback structurally.
if grep -q '"#elif defined __psp__\\n #define XASH_PSP 1\\n"' "$ROOT/scripts/apply-n64-port.py"; then
    echo "ERROR: stale r11 PSP/POSIX adjacency patch remains" >&2
    exit 1
fi
grep -q '_unique_line_index' "$ROOT/scripts/apply-n64-port.py"
grep -q 'POSIX fallback' "$ROOT/scripts/apply-n64-port.py"
STALE_PATH='3rdparty/library''-suffix'
if grep -R -n "$STALE_PATH" "$ROOT/scripts" "$ROOT/tests" "$ROOT/.github"; then
    echo "ERROR: stale hyphenated library-suffix path remains" >&2
    exit 1
fi

CHECK_REPO=$(mktemp -d)
trap 'rm -rf "$CHECK_REPO"' EXIT
cp -a "$ROOT/." "$CHECK_REPO/"
rm -rf "$CHECK_REPO/scripts/__pycache__" "$CHECK_REPO/tests/__pycache__"
git -c safe.directory="$CHECK_REPO" -C "$CHECK_REPO" init -q
git -c safe.directory="$CHECK_REPO" -C "$CHECK_REPO" add -A
git -c safe.directory="$CHECK_REPO" -C "$CHECK_REPO" diff --cached --check

echo "host-check: PASS"
