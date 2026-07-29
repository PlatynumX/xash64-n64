#ifndef MOCK_XASH_PLATFORM_H
#define MOCK_XASH_PLATFORM_H
#include <stddef.h>
typedef int qboolean;
#ifndef false
#define false 0
#endif
#ifndef true
#define true 1
#endif
typedef enum {
    ORIENTATION_UNKNOWN = 0,
    ORIENTATION_LANDSCAPE,
    ORIENTATION_LANDSCAPE_FLIPPED,
    ORIENTATION_PORTRAIT,
    ORIENTATION_PORTRAIT_FLIPPED
} platform_orientation_t;
#endif
