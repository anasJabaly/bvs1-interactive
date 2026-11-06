#include <stdint.h>
#include "process.h"

#define UART0_BASE 0x10000000UL
#define UART_THR 0
#define UART_LSR 5
#define UART_LSR_THRE 0x20

static volatile uint8_t *const uart0 =
    (volatile uint8_t *)UART0_BASE;

static void uart_putc(char c)
{
    while ((uart0[UART_LSR] & UART_LSR_THRE) == 0) {
    }
    uart0[UART_THR] = (uint8_t)c;
}

static void uart_puts(const char *s)
{
    while (*s != '\0') {
        if (*s == '\n') {
            uart_putc('\r');
        }
        uart_putc(*s++);
    }
}

static void permute(char value[])
{
    char tmp;

    tmp = value[0];
    value[0] = value[1];
    value[1] = tmp;

    uart_puts("process: before yield: ");
    uart_puts(value);
    uart_puts("\n");

    process_yield();

    tmp = value[2];
    value[2] = value[3];
    value[3] = tmp;
}

static void worker(void)
{
    char value[] = "BVS1";

    permute(value);

    uart_puts("process: result: ");
    uart_puts(value);
    uart_puts("\n");

    process_exit(0);
}

void main(void)
{
    struct process p;

    process_create(&p, worker);
    process_run(&p);

    if (p.state == READY) {
        uart_puts("os: process yielded\n");
    }

    process_run(&p);

    if (p.state == FINISHED) {
        uart_puts("os: process exited\n");
    }

    for (;;) {
    }
}
