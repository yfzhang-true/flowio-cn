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
#include "driver/gpio.h"
#include "esp_timer.h"
#include <stdio.h>
#include <string.h>

/* 充电宝/电池独立供电时无串口对端，上电自动跑呼吸演示循环（充→停→抽→停）。
 * 串口调试时按住 BOOT 键开机可禁用演示（GPIO0 拉低即跳过），
 * 否则演示会周期性改变阀/传感状态干扰测试。置 0 永久关闭。 */
#define PN_BOOT_DEMO 1

static void cli_delay_wrapper(uint32_t ms) { vTaskDelay(pdMS_TO_TICKS(ms)); }

#if PN_BOOT_DEMO
static void demo_task(void *arg)
{
    (void)arg;
    /* 上电后 30 秒内按住 BOOT（GPIO0 拉低）≥1 秒 → 本次跳过演示；
     * 30 秒后未按 → 自动开始呼吸演示循环（充电宝独立供电场景）。
     * 注意：复位瞬间不要按 BOOT（GPIO0 采样低会进下载模式挂起）——
     * 复位完成后再按。 */
    gpio_config_t io = {
        .pin_bit_mask = 1ULL << GPIO_NUM_0,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    gpio_config(&io);
    for (int i = 0; i < 600; ++i) {   /* 30s = 600×50ms */
        if (gpio_get_level(GPIO_NUM_0) == 0) {
            printf("[DEMO] BOOT held — demo disabled this session\n");
            vTaskDelete(NULL);
        }
        vTaskDelay(pdMS_TO_TICKS(50));
    }
    printf("[DEMO] breathing demo: I 6s -> S 3s -> V 6s -> S 3s loop\n");
    for (;;) {
        pn_cli_process_line("I 1 255");   /* 充气 */
        vTaskDelay(pdMS_TO_TICKS(6000));
        pn_cli_process_line("S 1");       /* 停止保压 */
        vTaskDelay(pdMS_TO_TICKS(3000));
        pn_cli_process_line("V 1 255");   /* 抽气 */
        vTaskDelay(pdMS_TO_TICKS(6000));
        pn_cli_process_line("S 1");
        vTaskDelay(pdMS_TO_TICKS(3000));
    }
}
#endif

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
#if PN_BOOT_DEMO
    xTaskCreate(demo_task, "pn_demo", 4096, NULL, 4, NULL);
#endif

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
