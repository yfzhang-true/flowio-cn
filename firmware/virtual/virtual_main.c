/**
 * virtual_main.c — 虚拟设备：无硬件的上位机调试入口
 *
 * pn_core 逻辑层跑在 mock HAL 上。除通用 CLI 外另有虚拟专属命令：
 *   M <idx> <kPa>   设置传感器模拟读数      例: M 0 45
 *   W <ms>          推进 mock 时钟          例: W 1000
 *   K               手动执行一次闭环 tick
 *   Q               退出
 */
#include "pn_core/actions.h"
#include "pn_core/closedloop.h"
#include "pn_core/cli.h"
#include "../tests/mock_hal.h"

#include <stdio.h>
#include <string.h>

int main(void)
{
    pn_mock_reset();
    pn_cli_set_delay_fn(pn_mock_advance_ms);   /* "延时"即时推进 mock 时钟 */
    pn_init(pn_mock_hal(), PN_CFG_GENERAL);

    printf("=== FlowIO P0 虚拟设备（mock HAL）===\n");
    printf("通用命令: I/V/R/S/O/C/G/X/F/P/T/L  虚拟命令: M <idx> <kPa> | W <ms> | K | Q\n");
    printf("state=0x%04X\n", (unsigned)pn_get_state());

    char line[64];
    for (;;) {
        if (!fgets(line, sizeof(line), stdin)) break;
        size_t n = strlen(line);
        if (n && (line[n - 1] == '\n' || line[n - 1] == '\r')) line[n - 1] = 0;
        if (!line[0]) continue;

        unsigned sidx, ms;
        float kpa;
        if (line[0] == 'M' && sscanf(line + 1, "%u %f", &sidx, &kpa) == 2
            && sidx < PN_SENSOR_COUNT) {
            pn_mock_sensor_kpa[sidx] = kpa;
            printf("sensor%u=%.2f kPa (sim)\n", sidx, (double)kpa);
            continue;
        }
        if (line[0] == 'W' && sscanf(line + 1, "%u", &ms) == 1) {
            pn_mock_advance_ms(ms);
            printf("clock+=%ums\n", ms);
            continue;
        }
        if (line[0] == 'K') {
            pn_cl_status_t cl = pn_inflate_to_tick();
            if (cl == PN_CL_DONE) {
                pn_inflate_job_t j;
                pn_inflate_to_get_job(&j);
                printf("[CL] done elapsed=%ums reached=%.1fkPa\n",
                       (unsigned)j.elapsed_ms, (double)j.reached_kpa);
            } else {
                printf("[CL] %d\n", (int)cl);   /* 0 IDLE 1 RUNNING 3 TIMEOUT 4 ERR */
            }
            continue;
        }
        if (line[0] == 'Q') { printf("bye\n"); break; }
        pn_cli_process_line(line);
    }
    return 0;
}
