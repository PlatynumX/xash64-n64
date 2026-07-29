#ifndef MOCK_LIBDRAGON_H
#define MOCK_LIBDRAGON_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
void timer_init(void);
void joypad_init(void);
bool debug_init_usblog(void);
bool debug_init_emulog(void);
bool debug_init_sdfs(const char *prefix, int partition);
void debug_close_sdfs(void);
size_t get_memory_size(void);
uint64_t get_ticks_us(void);
void wait_ms(unsigned long ms);
#endif
