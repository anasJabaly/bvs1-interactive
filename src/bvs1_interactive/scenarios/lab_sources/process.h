#ifndef BVS1_PROCESS_H
#define BVS1_PROCESS_H

#include "context.h"

#define STACK_SIZE 4096

typedef void (*process_entry_t)(void);

enum process_state {
    READY,
    RUNNING,
    FINISHED
};

struct process {
    process_entry_t entry;
    unsigned char stack[STACK_SIZE];
    struct context context;
    enum process_state state;
    int exit_status;
};

void process_create(struct process *process, process_entry_t entry);
void process_run(struct process *process);
void process_yield(void);
void process_exit(int status);

#endif
