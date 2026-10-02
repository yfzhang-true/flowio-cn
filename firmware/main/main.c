/**
 * main.c — P0 上电入口（目标机）
 *
 * 架构：control_task 以 10ms 周期跑（闭环 tick + 节能 + 超压保护 + 泵护栏
 *       + BLE 遥测组帧）；命令入口统一为 pn_cmd_feed()（S5 cmd_transport）：
 *       串口 fgets 与 BLE cmd 特征（经 ble_twin 队列任务）喂同一函数，
 *       行缓冲聚合 + 0xA5 帧翻译后走 pn_core/cli.c 分发（与虚拟设备共用）。
 */
#include "pn_core/actions.h"
#include "pn_core/closedloop.h"
#include "pn_core/cli.h"
#include "pn_core/proto.h"      /* S5: 0xA5 帧命令翻译（BLE cmd 特征） */
#include "pn_core/tca9548.h"    /* S4: tca_bind 注入真机 I2C 写 */
#include "pn_hal_esp32/hal_esp32.h"
#include "pn_hal_esp32/ble_twin.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
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

/* ---------- cmd_transport 统一分发（S5，BLE.md §1/§3.2） ----------
 * 串口 fgets 与 BLE cmd write 都喂 pn_cmd_feed()：字节流先按 0xA5 二进制帧
 * 或 ASCII 行聚合（跨多次 write 分片的行也能拼上），完整后翻译成 CLI 行，
 * 与串口走同一个 pn_cli_process_line()。互斥锁串行化三个调用线程
 * （串口主循环 / BLE cmd 任务 / 演示任务）。 */
static SemaphoreHandle_t s_cmd_mtx;
static char     s_line[64];
static size_t   s_line_n;
static uint8_t  s_frame[5];
static size_t   s_frame_n;
static bool     s_in_frame;

static void dispatch_line(char *line)
{
    if (line[0] == 'W' && line[1] == 0)
        pn_hal_esp32_i2c_scan();   /* bring-up 诊断：I2C 全总线扫描 */
    else if (line[0] == 'M') {
        /* 舵机诊断：M <gpio> <usec> —— LEDC 精确时基发 50Hz 舵机脉冲 */
        int gpio = 17, usec = 2500;
        if (sscanf(line + 1, "%d %d", &gpio, &usec) >= 1)
            pn_hal_esp32_servo_le_test(gpio, usec);
    }
    else
        pn_cli_process_line(line);
}

/* 0xA5 帧 → 等价 CLI 行（BLE.md §3.2 翻译表；CRC 已在调用处校验） */
static void frame_to_line(const uint8_t f[5], char *out, size_t cap)
{
    switch ((char)f[1]) {
    case PN_CMD_INFLATE: snprintf(out, cap, "I %u %u", f[2], f[3]); break;
    case PN_CMD_VACUUM:  snprintf(out, cap, "V %u %u", f[2], f[3]); break;
    case PN_CMD_RELEASE: snprintf(out, cap, "R %u", f[2]);          break;
    case PN_CMD_STOP:    snprintf(out, cap, "S %u", f[2]);          break;
    case PN_CMD_OPEN:    snprintf(out, cap, "O %u", f[2]);          break;
    case PN_CMD_CLOSE:   snprintf(out, cap, "C %u", f[2]);          break;
    case PN_CMD_QUERY:   snprintf(out, cap, "P");                   break;
    case PN_CMD_STATE:   snprintf(out, cap, "T");                   break;
    case PN_CMD_RESET:   snprintf(out, cap, "X");                   break;
    default:             snprintf(out, cap, "?");                   break;
    }
}

void pn_cmd_feed(const uint8_t *buf, size_t len)
{
    char cooked[24];
    for (size_t i = 0; i < len; ++i) {
        uint8_t b = buf[i];

        /* 二进制帧模式：行缓冲空时见 0xA5 进入，收满 5 字节校验后翻译 */
        if (s_in_frame || (b == PN_PROTO_MAGIC && s_line_n == 0 && s_frame_n == 0)) {
            s_in_frame = true;
            s_frame[s_frame_n++] = b;
            if (s_frame_n < sizeof(s_frame)) continue;
            s_frame_n = 0;
            s_in_frame = false;
            if (s_frame[4] == pn_proto_crc8(s_frame, 4)) {   /* 坏帧静默丢弃 */
                frame_to_line(s_frame, cooked, sizeof(cooked));
                xSemaphoreTake(s_cmd_mtx, portMAX_DELAY);
                dispatch_line(cooked);
                xSemaphoreGive(s_cmd_mtx);
            }
            continue;
        }

        if (b == '\n' || b == '\r') {
            if (s_line_n) {
                s_line[s_line_n] = 0;
                s_line_n = 0;
                xSemaphoreTake(s_cmd_mtx, portMAX_DELAY);
                dispatch_line(s_line);
                xSemaphoreGive(s_cmd_mtx);
            }
            continue;
        }
        if (s_line_n < sizeof(s_line) - 1)
            s_line[s_line_n++] = (char)b;
        else
            s_line_n = 0;   /* 超长行整行丢弃（BLE.md：命令行 ≤63B） */
    }
}

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
        pn_cmd_feed((const uint8_t *)"I 1 255\n", 8);    /* 充气 */
        vTaskDelay(pdMS_TO_TICKS(6000));
        pn_cmd_feed((const uint8_t *)"S 1\n", 4);        /* 停止保压 */
        vTaskDelay(pdMS_TO_TICKS(3000));
        pn_cmd_feed((const uint8_t *)"V 1 255\n", 8);    /* 抽气 */
        vTaskDelay(pdMS_TO_TICKS(6000));
        pn_cmd_feed((const uint8_t *)"S 1\n", 4);
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

        pn_optimize_power(ble_twin_hold_duty(), ble_twin_hold_delay_ms());  /* S5: Config 服务 RAM 镜像（默认值=原宏） */
        pn_check_overpressure(120.f);
        pn_hal_esp32_servo_refresh();                           /* 舵机 50Hz 脉冲流（单次发送非循环） */
        board_led_set(pn_get_state() ? 1 : 0);   /* S4 简化映射：任一执行器动作=RUNNING 绿，否则 IDLE 呼吸蓝 */
        board_led_tick_10ms();                   /* WS2812 呼吸/闪烁状态机（10ms 节拍驱动） */
        ble_twin_tick_10ms();                    /* S5: 每 100ms 组 20B state notify（notify_en 开才发） */
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
    s_cmd_mtx = xSemaphoreCreateMutex();          /* S5: 命令三入口（串口/BLE/演示）串行化 */
    printf("[BOOT] hal init...\n"); fflush(stdout);
    pn_init(pn_hal_esp32_init(), PN_CFG_GENERAL);
    tca_bind(tca_hal_write);      /* S4: pn_core TCA9548A 逻辑层绑定真机 I2C 写（QEMU 下恒 -1，无害） */
    board_led_init();             /* S4: 板载 WS2812 状态灯（QEMU 无 RMT，内部跳过） */
    ble_twin_init();              /* S5: BLE 四服务（QEMU/无 BT 内部安全跳过） */
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
            /* S5: 串口与 BLE cmd 特征同一入口（含行尾符，行缓冲在 pn_cmd_feed 内） */
            pn_cmd_feed((const uint8_t *)line, strlen(line));
        }
    }
}
