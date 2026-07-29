#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

python3 -m py_compile \
    "$ROOT/scripts/audit-xash-upstream.py" \
    "$ROOT/scripts/apply-n64-port.py" \
    "$ROOT/scripts/prepare-uplink.py" \
    "$ROOT/tests/test-r9-integration.py" \
    "$ROOT/tests/test-prepare-uplink.py"

for script in "$ROOT"/scripts/*.sh "$ROOT"/tests/*.sh; do
    bash -n "$script"
done

python3 "$ROOT/tests/test-r9-integration.py"
python3 "$ROOT/tests/test-prepare-uplink.py"

gcc -std=gnu17 -Wall -Wextra -Werror -fsyntax-only \
    -I"$ROOT/tests/mock_xash" \
    -I"$ROOT/tests/mock_libdragon" \
    "$ROOT/xash-overlay/engine/platform/n64/sys_n64.c"

# Regression guards for the real current-Xash static-link route.
grep -q -- '--enable-static-binary' "$ROOT/scripts/build-xash-r9.sh"
grep -q -- '--static-linking=filesystem_stdio' "$ROOT/scripts/build-xash-r9.sh"
grep -q 'mips64-elf-' "$ROOT/scripts/build-xash-r9.sh"
grep -q 'TOOLWRAP' "$ROOT/scripts/build-xash-r9.sh"
grep -q '3rdparty/library_suffix' "$ROOT/scripts/apply-n64-port.py"
STALE_PATH='3rdparty/library''-suffix'
if grep -R -n "$STALE_PATH" "$ROOT/scripts" "$ROOT/tests" "$ROOT/.github"; then
    echo "ERROR: stale hyphenated library-suffix path remains" >&2
    exit 1
fi

CHECK_REPO=$(mktemp -d)
trap 'rm -rf "$CHECK_REPO"' EXIT
cp -a "$ROOT/." "$CHECK_REPO/"
rm -rf "$CHECK_REPO/scripts/__pycache__" "$CHECK_REPO/tests/__pycache__"
git -C "$CHECK_REPO" init -q
git -C "$CHECK_REPO" add -A
git -C "$CHECK_REPO" diff --cached --check

echo "host-check: PASS"
