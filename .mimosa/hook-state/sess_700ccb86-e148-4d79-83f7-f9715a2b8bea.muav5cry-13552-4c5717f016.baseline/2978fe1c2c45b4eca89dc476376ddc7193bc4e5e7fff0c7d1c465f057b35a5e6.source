/**
 * main.c — P0 上电入口 + 串口 CLI（装配指南第 4-7 步的驱动台）
 *
 * 架构：control_task 以 10ms 周期跑（闭环 tick + 节能 + 超压保护）；
 *       主线程阻塞在串口 CLI（阻塞不影响控制节拍）。
 *
 * CLI 命令（ASCII 行，\n 结尾）：
 *   I <ports> <pwm>   充气       例: I 1 255
 *   V <ports> <pwm>   抽气
 *   R <ports>         释放
 *   S <ports>         停止/保压
 *   O <ports> / C <ports>   开/关端口阀
 *   P                 读两只传感器
 *   T                 打印状态字
 *   L                 阀保持节能
 */
#include "pn_core/actions.h"
#include "pn_core/closedloop.h"
#include "pn_hal_esp32/hal_esp32.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>
#include <string.h>

#define PN_OVERPRESSURE_LIMIT_KPA 120.f

static void control_task(void *arg)
{
    (void)arg;
    for (;;) {
        pn_cl_status_t cl = pn_inflate_to_tick();
        if (cl == PN_CL_DONE) {
            pn_inflate_job_t j;
            pn_inflate_to_get_job(&j);
            printf("[CL] done elapsed=%ums reached=%.1fkPa\n",
                   (unsigned)j.elapsed_ms, (double)j.reached_kpa);
        } else if (cl == PN_CL_TIMEOUT) {
            printf("[CL] timeout, aborted\n");
        } else if (cl == PN_CL_ERR) {
            printf("[CL] sensor error, aborted\n");
        }

        pn_optimize_power(PN_HOLD_DEFAULT_DUTY, PN_HOLD_DEFAULT_DELAY_MS);
        pn_check_overpressure(PN_OVERPRESSURE_LIMIT_KPA);
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

static void cli_task_line(char *line)
{
    float kpa;
    uint8_t ports, pwm;
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
    case 'O':
        if (sscanf(line + 1, "%hhu", &ports) == 1) pn_ports_open(ports);
        break;
    case 'C':
        if (sscanf(line + 1, "%hhu", &ports) == 1) pn_ports_close(ports);
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
        pn_optimize_power(PN_HOLD_DEFAULT_DUTY, PN_HOLD_DEFAULT_DELAY_MS);
        printf("optimized\n");
        break;
    default:
        printf("?\n");
    }
}

void app_main(void)
{
    pn_init(pn_hal_esp32_init(), PN_CFG_GENERAL);
    printf("FlowIO-compatible P0 ready. state=0x%04X\n", (unsigned)pn_get_state());

    xTaskCreate(control_task, "pn_ctrl", 4096, NULL, 5, NULL);

    char line[64];
    for (;;) {
        if (fgets(line, sizeof(line), stdin)) {
            size_t n = strlen(line);
            if (n && (line[n - 1] == '\n' || line[n - 1] == '\r')) line[n - 1] = 0;
            if (line[0]) cli_task_line(line);
        }
    }
}
