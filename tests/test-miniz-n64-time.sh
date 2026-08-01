#!/usr/bin/env bash
set -euo pipefail
TD=$(mktemp -d)
trap 'rm -rf "$TD"' EXIT
cat > "$TD/test.c" <<'SRC'
#include <string.h>
#include <time.h>
#include <utime.h>
typedef int mz_bool;
typedef time_t MZ_TIME_T;
#define MZ_TRUE 1
static mz_bool mz_zip_set_file_times(const char *pFilename, MZ_TIME_T access_time, MZ_TIME_T modified_time)
{
#if defined(N64) || defined(__N64__)
    /* libdragon filesystems do not provide writable file timestamps. */
    (void)pFilename;
    (void)access_time;
    (void)modified_time;
    return MZ_TRUE;
#else
    struct utimbuf t;

    memset(&t, 0, sizeof(t));
    t.actime = access_time;
    t.modtime = modified_time;

    return !utime(pFilename, &t);
#endif
}
int main(void)
{
    return mz_zip_set_file_times("unused", 0, 0) ? 0 : 1;
}
SRC
gcc -std=gnu17 -Wall -Wextra -Werror -DN64 -fsyntax-only "$TD/test.c"
gcc -std=gnu17 -Wall -Wextra -Werror -fsyntax-only "$TD/test.c"
echo "test-miniz-n64-time: PASS"
