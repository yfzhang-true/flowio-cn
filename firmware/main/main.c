/**
 * main.c — P0 上电入口（目标机）
 *
 * 架构：control_task 以 10ms 周期跑（闭环 tick + 节能 + 超压保护 + 泵护栏）；
 *       主线程阻塞在串口 CLI（命令分发在 pn_core/cli.c，与虚拟设备共用）。
 */
#include "pn_core/actions.h"
#include "pn_core/closedloop.h"
#include "pn_core/cli.h"
#include "pn_core/leak_detect.h"
#include "pn_hal_esp32/hal_esp32.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "driver/uart_vfs.h"
#include "esp_timer.h"
#include <stdio.h>
#include <string.h>

static void cli_delay_wrapper(uint32_t ms) { vTaskDelay(pdMS_TO_TICKS(ms)); }

static void control_task(void *arg)
{
    (void)arg;
    uint32_t pump_on_since = 0;
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

        /* 泵连续运行护栏：超时强制停止（防干转/过热） */
        if (pn_get_state_of(7)) {
            uint32_t now_ms = (uint32_t)(esp_timer_get_time() / 1000);
            if (pump_on_since == 0) pump_on_since = now_ms;
            else if (now_ms - pump_on_since > 120000u) {
                pn_pump_stop();
                printf("[SAFETY] pump max runtime, stopped\n");
                pump_on_since = 0;
            }
        } else pump_on_since = 0;

        pn_optimize_power(PN_HOLD_DEFAULT_DUTY, PN_HOLD_DEFAULT_DELAY_MS);
        pn_check_overpressure(120.f);
        pn_ml_tick((uint32_t)(esp_timer_get_time() / 1000));   /* TinyML 20Hz 采样（内部节流） */
        pn_hal_esp32_servo_refresh();                           /* 舵机 50Hz 脉冲流（单次发送非循环） */
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void app_main(void)
{
    /* 真机 stdin 需要 UART 驱动 + VFS 桥接（默认 console 只配输出——fgets 收不到；
     * 2026-09-23 真机首次点亮实证。QEMU 的 UART 模型走轮询读，跳过以免驱动中断差异） */
    if (!pn_hal_esp32_is_qemu()) {
        uart_driver_install(CONFIG_ESP_CONSOLE_UART_NUM, 256, 0, 0, NULL, 0);
        uart_vfs_dev_use_driver(CONFIG_ESP_CONSOLE_UART_NUM);
    }
    pn_cli_set_delay_fn(cli_delay_wrapper);
    printf("[BOOT] hal init...\n"); fflush(stdout);
    pn_init(pn_hal_esp32_init(), PN_CFG_GENERAL);
    printf("[BOOT] pn_init done\n"); fflush(stdout);
    printf("FlowIO-compatible P0 ready. state=0x%04X\n", (unsigned)pn_get_state());
    fflush(stdout);

    xTaskCreate(control_task, "pn_ctrl", 4096, NULL, 5, NULL);

    char line[64];
    for (;;) {
        if (fgets(line, sizeof(line), stdin)) {
            size_t n = strlen(line);
            if (n && (line[n - 1] == '\n' || line[n - 1] == '\r')) line[n - 1] = 0;
            if (!line[0]) continue;
            if (line[0] == 'W' && line[1] == 0)
                pn_hal_esp32_i2c_scan();   /* bring-up 诊断：I2C 全总线扫描 */
            else
                pn_cli_process_line(line);
        }
    }
}
