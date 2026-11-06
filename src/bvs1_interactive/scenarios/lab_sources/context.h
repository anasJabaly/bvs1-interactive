#ifndef BVS1_CONTEXT_H
#define BVS1_CONTEXT_H
#include <stdint.h>

struct context {
    uintptr_t ra;
    uintptr_t sp;
    uintptr_t s[12];
};

void context_switch(struct context *current_context,
                    struct context *next_context);
#endif
