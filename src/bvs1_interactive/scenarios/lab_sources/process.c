#include "process.h"

static struct context os_context;
static struct process *current_process;

static void process_start(void)
{
    current_process->entry();
    process_exit(0);

    for (;;) {
    }
}

void process_create(struct process *process, process_entry_t entry)
{
    process->entry = entry;
    process->exit_status = 0;

    uintptr_t stack_top =
        (uintptr_t)(process->stack + STACK_SIZE);
    stack_top &= ~(uintptr_t)15;

    process->context.sp = stack_top;
    process->context.ra = (uintptr_t)process_start;

    for (int i = 0; i < 12; ++i) {
        process->context.s[i] = 0;
    }

    process->state = READY;
}

void process_run(struct process *process)
{
    if (process->state != READY) {
        return;
    }

    current_process = process;
    process->state = RUNNING;

    context_switch(&os_context, &process->context);

    current_process = 0;
}

void process_yield(void)
{
    struct process *process = current_process;

    process->state = READY;
    context_switch(&process->context, &os_context);
}

void process_exit(int status)
{
    struct process *process = current_process;

    process->exit_status = status;
    process->state = FINISHED;

    context_switch(&process->context, &os_context);

    for (;;) {
    }
}
