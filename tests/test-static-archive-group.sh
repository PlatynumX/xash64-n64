#!/usr/bin/env bash
set -euo pipefail

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

cat > main.c <<'SRC'
extern int dragon_entry(void);
int main(void) { return dragon_entry() != 42; }
SRC
cat > dragon.c <<'SRC'
extern int newlib_value(void);
int dragon_entry(void) { return newlib_value(); }
SRC
cat > newlib.c <<'SRC'
extern int dragony_sys_value(void);
int newlib_value(void) { return dragony_sys_value(); }
SRC
cat > dragony_sys.c <<'SRC'
int dragony_sys_value(void) { return 42; }
SRC

cc -c main.c dragon.c newlib.c dragony_sys.c
ar rcs libc_mock.a newlib.o
ar rcs libdragon_mock.a dragon.o
ar rcs libdragonsys_mock.a dragony_sys.o

# Mirrors the r14 ordering: libc is scanned before libdragon introduces the
# unresolved newlib symbol. A one-pass archive link must fail.
if cc main.o libc_mock.a libdragon_mock.a libdragonsys_mock.a -o ungrouped 2>/dev/null; then
    echo "ERROR: ungrouped static-archive regression unexpectedly linked" >&2
    exit 1
fi

# GNU ld groups rescan the mutually dependent archives until all references are
# resolved, matching the r15 N64 link contract.
cc main.o \
    -Wl,--start-group libc_mock.a libdragon_mock.a libdragonsys_mock.a -Wl,--end-group \
    -o grouped
./grouped

echo "test-static-archive-group: PASS"
