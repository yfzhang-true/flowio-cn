/**
 * pn_core/cli.c — CLI 分发实现（从 main.c 抽出，双宿主共用）
 */
#include "pn_core/cli.h"
#include "pn_core/closedloop.h"

#include <stdio.h>
#include <string.h>

#define PN_OVERPRESSURE_LIMIT_KPA 120.f
#define PN_HOLD_DUTY_DEFAULT      PN_HOLD_DEFAULT_DUTY
#define PN_HOLD_MS_DEFAULT        PN_HOLD_DEFAULT_DELAY_MS

static pn_cli_delay_fn_t s_delay;

void pn_cli_set_delay_fn(pn_cli_delay_fn_t fn) { s_delay = fn; }

static void cli_delay(uint32_t ms) { if (s_delay) s_delay(ms); }

void pn_cli_selftest(void)
{
    printf("[ST] 1. sensor detect: ");
    for (uint8_t i = 0; i < PN_SENSOR_COUNT; ++i) {
        float p;
        printf("S%u=%s ", i, pn_read_pressure(i, &p) == PN_OK ? "OK" : "ABSENT");
    }
    printf("\n[ST] 2. valve click test (3 port clicks + inlet + vent):\n");
    for (uint8_t v = 0; v < 3; ++v) {
        printf("  port valve %u ON/OFF\n", v + 1);
        pn_ports_open((uint8_t)(1u << v));
        cli_delay(250);
        pn_ports_close((uint8_t)(1u << v));
        cli_delay(250);
    }
    printf("  inlet servo ON/OFF\n");
    pn_inlet_open();  cli_delay(400); pn_inlet_close();
    cli_delay(250);
    printf("  vent servo ON/OFF\n");
    pn_vent_open();   cli_delay(400); pn_vent_close();
    cli_delay(250);

    printf("[ST] 3. manifold delta-P test (pump 1.5s, ports closed):\n");
    float p0, p1;
    pn_read_pressure(0, &p0);
    pn_inlet_open();
    pn_pump_start(255);
    cli_delay(1500);
    pn_pump_stop();
    pn_inlet_close();
    pn_read_pressure(0, &p1);
    printf("  dP=%.2f kPa (%.2f -> %.2f) %s\n", (double)(p1 - p0), (double)p0, (double)p1,
           (p1 - p0 > 2.f) ? "PASS" : "FAIL/LEAK");
    printf("[ST] done\n");
}

void pn_cli_process_line(char *line)
{
    float kpa;
    uint8_t ports, pwm, sensor;
    switch (line[0]) {
    case 'I':
        if (sscanf(line + 1, "%hhu %hhu", &ports, &pwm) == 2)
            printf("inflate=%d\n", pn_start_inflation(ports, pwm));
        break;
    case 'V':
        if (sscanf(line + 1, "%hhu %hhu", &ports, &pwm) == 2)
            printf("vacuum=%d\n", pn_start_vacuum(ports, pwm));
        break;
    case 'R':
        if (sscanf(line + 1, "%hhu", &ports) == 1)
            printf("release=%d\n", pn_start_release(ports));
        break;
    case 'S':
        if (sscanf(line + 1, "%hhu", &ports) == 1)
            printf("stop=%d\n", pn_stop_action(ports));
        break;
    case 'H':
        if (sscanf(line + 1, "%hhu", &ports) == 1)
            printf("hold_open=%d\n", pn_hold_open(ports));   /* 诊断保压：泵侧密封+端口保持通 */
        break;
    case 'O':
        if (sscanf(line + 1, "%hhu", &ports) == 1) pn_ports_open(ports);
        break;
    case 'C':
        if (sscanf(line + 1, "%hhu", &ports) == 1) pn_ports_close(ports);
        break;
    case 'G': {   /* 闭环充气: G <ports> <target_kPa> <sensor_idx> */
        if (sscanf(line + 1, "%hhu %f %hhu", &ports, &kpa, &sensor) == 3)
            printf("inflate_to=%d\n", pn_inflate_to_start(ports, kpa, sensor, 255, 30000));
        break;
    }
    case 'X':
        pn_cl_reset();
        printf("closed-loop reset\n");
        break;
    case 'F':
        printf("[ST] selftest starting\n");
        pn_cli_selftest();
        break;
    case 'P':
        for (uint8_t i = 0; i < PN_SENSOR_COUNT; ++i)
            if (pn_read_pressure(i, &kpa) == PN_OK) printf("sensor%u=%.2f kPa\n", i, (double)kpa);
            else printf("sensor%u=ERR\n", i);
        break;
    case 'T':
        printf("state=0x%04X err=%d\n", (unsigned)pn_get_state(), pn_last_error());
        break;
    case 'L':
        pn_optimize_power(PN_HOLD_DUTY_DEFAULT, PN_HOLD_MS_DEFAULT);
        printf("optimized\n");
        break;
    default:
        printf("?\n");
    }
}
