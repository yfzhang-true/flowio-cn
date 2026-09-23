/**
 * pn_hal_esp32.c — ESP32-S3 硬件层实现（目标板：YD-ESP32-S3 / HW-678A，N16R8）
 *
 * 引脚分配（study-notes/10 第三节，与 P0 实际接线一致）：
 *   阀:  PORT1=4 PORT2=5 PORT3=6 PORT4=7 PORT5=10 INLET=11 VENT=12   (LEDC ch0-6)
 *   泵:  GPIO21                                                       (LEDC ch7)
 *   kit 舵机开关: 泵=15 充气=16 吸气=17                                (RMT ch0-2)
 *   I2C: SDA=8 SCL=9（XGZP6897D + TCA9548A）
 *
 * 板卡事实（厂商资料包 SCH-V1.4 + 产品介绍，2026-09-22 验证）：
 *   - 板载 WS2812 RGB 指示灯 = GPIO48（地址型，非普通 GPIO；状态灯待加时用它）
 *   - 双 Type-C：丝印 COM 的口走 CH343P 串口（烧录/monitor 用它）；
 *     另一口 USB-OTG 需焊 0Ω 桥接才可用，P0 不用
 *   - BOOT 键=GPIO0，RST 键=EN；出厂固件为 AP 模式（RGB 连上 WiFi 才亮）
 *   - N16R8 的 PSRAM 是 Octal（sdkconfig 已改 SPIRAM_MODE_OCT@80M），
 *     ⚠️ GPIO35/36/37 被 Octal PSRAM 独占，本文件所有引脚已避开
 *
 * 铁律：阀全走 LEDC（开=255 满占空比，保持=降占空比），绝不用纯数字写。
 */
#include "pn_hal_esp32/hal_esp32.h"

#include "driver/ledc.h"
#include "driver/rmt_tx.h"
#include "driver/i2c_master.h"
#include "esp_timer.h"
#include "esp_check.h"
#include "hal/efuse_hal.h"

#include <string.h>

#define PN_LED_FREQ_HZ      1000
#define PN_LED_RESOLUTION   LEDC_TIMER_8_BIT
#define PN_SERVO_RES_US     1000000        /* RMT 1MHz：1 tick = 1us */
#define PN_SERVO_PERIOD_US  20000

/* 引脚表 */
static const gpio_num_t s_valve_gpio[PN_VALVE_COUNT] = {
    GPIO_NUM_4, GPIO_NUM_5, GPIO_NUM_6, GPIO_NUM_7, GPIO_NUM_10,
    GPIO_NUM_11, GPIO_NUM_12,
};
#define PN_PUMP_GPIO  GPIO_NUM_21

static const gpio_num_t s_servo_gpio[3] = {
    GPIO_NUM_15, GPIO_NUM_16, GPIO_NUM_17,
};

/* I2C — XGZP6897D-C（数字 IIC 差压，手册 V1.1）经 TCA9548A 模块分通道
 * 2026-09-23 依据：XGZP6897D-C 手册 V1.1 + CJMCU-9548 模块资料（拨码/例程核对）
 * 🔴 修正史（对照手册，原实现到货必炸）：
 *   ① 传感器地址 0x6D/0x5D 错 → 固定 0x58（-C 型不可定制）
 *   ② "写 0x30←0x0A 启动转换"协议错 → 从 0x04 连读 5 字节（ASIC 自动刷新）
 *   ③ K 因子 2^24/span 错 → P[Pa]=补码和/2^21×(PMAX−PMIN)（差 8 倍）
 *   ④ 两只 0x58 同挂一条总线冲突 → TCA9548A 通道切换（传感器#1→CH0，#2→CH1）
 * TCA9548A 模块（CJMCU-9548）：拨码 A2A1A0 默认全'0'→地址 0x70（可拨 0x70~0x77）；
 * 通道选择 = 向 0x70 写 1 字节 (1<<ch)；模块主侧/各通道侧均带上拉。
 * 传感器时序：上电 24ms、响应 2.5ms@OSR1024 —— 均 <50ms tick，可忽略 */
static i2c_master_bus_handle_t s_i2c_bus;
static i2c_master_dev_handle_t s_tca_dev;     /* TCA9548A @0x70 */
static i2c_master_dev_handle_t s_xgzp_dev;    /* 传感器 @0x58（通道切换后复用） */
static bool s_tca_present;
static bool s_xgzp_present[2];
static uint8_t s_xgzp_ch[2] = { 0, 1 };       /* 传感器#1→CH0，传感器#2→CH1 */
static int tca_select(uint8_t ch);            /* 定义见 xgzp_read_kpa 前 */
#define TCA9548A_ADDR   0x70
#define XGZP_ADDR       0x58      /* 7 位地址，-C 型固定（选型码 C） */
#define XGZP_REG_PDATA  0x04      /* 连读 5 字节：3=压力24bit补码 + 2=温度16bit */
#define XGZP_SPAN_PA    200000.0f /* ±100kPa 型（C100KPDPN）：PMAX−PMIN */
#define XGZP_TWO_POW_21 2097152.0f

/* ---------- 阀/泵：LEDC（端口阀）+ RMT 舵机（kit 方向阀/泵） ----------
 * 硬件映射（P0，见 study-notes/10）：
 *   固件 idx0-4（PORT1-5）→ MOS 模块 CH1-5 → 5 只常闭端口阀（LEDC PWM，支持保持降压）
 *   固件 idx5（INLET 角色）→ kit 充气三通阀（舵机：ON=接泵充气口，OFF=通大气）
 *   固件 idx6（VENT 角色）→ kit 吸气三通阀（舵机：ON=接泵吸气口，OFF=通大气）
 *   泵 → kit 泵舵机开关（ON/OFF）；MOS 备用通道留给泵 PWM 调速实验
 * ⚠️ 舵机两个位置的气动语义（ON=充气位还是排气位）在首次上电时标定（装配指南 3.5 步），
 *    标定后如与本文件相反，交换 s_servo_invert 或调换映射即可。
 */
static void pn_valve_write(uint8_t idx, uint8_t duty)
{
    if (idx == 5) {          /* INLET → kit 充气三通阀舵机 */
        pn_hal_esp32_servo_set(1, duty ? 2500 : 500);
        return;
    }
    if (idx == 6) {          /* VENT → kit 吸气三通阀舵机 */
        pn_hal_esp32_servo_set(2, duty ? 2500 : 500);
        return;
    }
    ledc_set_duty(LEDC_LOW_SPEED_MODE, (ledc_channel_t)idx, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, (ledc_channel_t)idx);
}

static void pn_pump_write(uint8_t idx, uint8_t duty)
{
    (void)idx;   /* P0 单泵 */
    pn_hal_esp32_servo_set(0, duty ? 2500 : 500);   /* 泵开关舵机：开/关 */
}

static void ledc_init_all(void)
{
    ledc_timer_config_t t = {
        .speed_mode      = LEDC_LOW_SPEED_MODE,
        .timer_num       = LEDC_TIMER_0,
        .duty_resolution = PN_LED_RESOLUTION,
        .freq_hz         = PN_LED_FREQ_HZ,
        .clk_cfg         = LEDC_AUTO_CLK,
    };
    ESP_ERROR_CHECK(ledc_timer_config(&t));

    ledc_channel_config_t ch = { 0 };
    ch.speed_mode = LEDC_LOW_SPEED_MODE;
    ch.timer_sel  = LEDC_TIMER_0;
    ch.duty       = 0;
    ch.hpoint     = 0;
    ch.flags.output_invert = false;
    for (int i = 0; i < PN_VALVE_COUNT; ++i) {
        ch.gpio_num = s_valve_gpio[i];
        ch.channel  = (ledc_channel_t)i;
        /* 优雅降级：单通道失败（外设缺失）不阻断系统 */
        if (ledc_channel_config(&ch) != ESP_OK)
            printf("[HAL] ledc ch%d config failed\n", i);
    }
    ch.gpio_num = PN_PUMP_GPIO;
    ch.channel  = LEDC_CHANNEL_7;
    if (ledc_channel_config(&ch) != ESP_OK)
        printf("[HAL] ledc pump ch config failed\n");
}

/* ---------- kit 舵机开关：RMT 50Hz ---------- */
static rmt_channel_handle_t s_servo_rmt[3];
static rmt_encoder_handle_t s_servo_enc[3];
static bool s_servo_ok[3];        /* RMT 通道不可用时优雅降级（QEMU 无 RMT 外设，2026-09-22 验证） */

static size_t rmt_encoder_callback(const void *data, size_t data_size,
                                   size_t symbols_written, size_t symbols_free,
                                   rmt_symbol_word_t *symbols, bool *done, void *arg)
{
    (void)data_size; (void)symbols_written; (void)arg;
    if (symbols_free < 1) { *done = true; return 0; }
    uint16_t pulse = *(const uint16_t *)data;
    symbols[0].duration0 = pulse;                          /* 高电平 = 脉宽 */
    symbols[0].level0     = 1;
    symbols[0].duration1  = PN_SERVO_PERIOD_US - pulse;    /* 低电平 = 周期余量 */
    symbols[0].level1     = 0;
    *done = true;
    return 1;                                              /* 编码了 1 个符号对 */
}

void pn_hal_esp32_servo_set(uint8_t switch_idx, uint16_t pulse_us)
{
    if (switch_idx >= 3 || !s_servo_ok[switch_idx]) return;
    if (pulse_us < 500)  pulse_us = 500;
    if (pulse_us > 2500) pulse_us = 2500;
    static uint16_t pulses[3];
    pulses[switch_idx] = pulse_us;
    rmt_transmit_config_t cfg = { .loop_count = -1 };
    rmt_transmit(s_servo_rmt[switch_idx], s_servo_enc[switch_idx],
                 &pulses[switch_idx], sizeof(uint16_t), &cfg);
}

static bool pn_is_qemu(void)
{
    /* espressif QEMU 报芯片版本 v0.0（真实 S3 无此版本）。
     * QEMU 不仿真 RMT/I2C：通道注册可能"成功"但 transmit 等不到中断→死等。 */
    return efuse_hal_get_major_chip_version() == 0 &&
           efuse_hal_get_minor_chip_version() == 0;
}

static void servo_init_all(void)
{
    if (pn_is_qemu()) {
        printf("[HAL] QEMU detected (chip v0.0), skip servos & i2c\n");
        return;
    }
    rmt_tx_channel_config_t tx = { 0 };
    tx.clk_src           = RMT_CLK_SRC_DEFAULT;
    tx.resolution_hz     = PN_SERVO_RES_US;
    tx.mem_block_symbols = 64;
    tx.trans_queue_depth = 1;
    for (int i = 0; i < 3; ++i) {
        tx.gpio_num = s_servo_gpio[i];
        /* 优雅降级：RMT 通道注册失败（QEMU 不仿真 RMT）时跳过该舵机，
         * 真机不会走到此分支；CLI/闭环照常运行。 */
        if (rmt_new_tx_channel(&tx, &s_servo_rmt[i]) != ESP_OK) {
            printf("[HAL] servo %d unavailable (no RMT channel; QEMU?)\n", i);
            s_servo_ok[i] = false;
            continue;
        }
        s_servo_ok[i] = true;

        rmt_simple_encoder_config_t enc_cfg = {
            .callback = rmt_encoder_callback,
        };
        ESP_ERROR_CHECK(rmt_new_simple_encoder(&enc_cfg, &s_servo_enc[i]));
        ESP_ERROR_CHECK(rmt_enable(s_servo_rmt[i]));
        pn_hal_esp32_servo_set(i, 0);      /* 0=不上舵机脉冲? 归 500us 全关位 */
    }
}

/* ---------- I2C / XGZP6897D ---------- */
static void i2c_init_all(void)
{
    /* QEMU 下 I2C 驱动会挂起（非报错），传感器在仿真里也不存在 */
    if (pn_is_qemu()) {
        s_xgzp_present[0] = s_xgzp_present[1] = false;
        return;
    }
    i2c_master_bus_config_t bus = { 0 };
    bus.i2c_port  = I2C_NUM_0;
    bus.sda_io_num = GPIO_NUM_8;
    bus.scl_io_num = GPIO_NUM_9;
    bus.clk_source = I2C_CLK_SRC_DEFAULT;
    bus.glitch_ignore_cnt = 7;
    bus.flags.enable_internal_pullup = true;   /* 模块板载上拉为主，内部上拉兜底 */
    /* 优雅降级：I2C 总线不可用（QEMU）时标记传感器缺失，闭环照常报传感器错 */
    if (i2c_new_master_bus(&bus, &s_i2c_bus) != ESP_OK) {
        printf("[HAL] i2c bus unavailable\n");
        s_xgzp_present[0] = s_xgzp_present[1] = false;
        return;
    }

    i2c_device_config_t tca = { 0 };
    tca.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    tca.device_address  = TCA9548A_ADDR;
    tca.scl_speed_hz    = 100000;
    s_tca_present = (i2c_master_bus_add_device(s_i2c_bus, &tca, &s_tca_dev) == ESP_OK);

    i2c_device_config_t dev = { 0 };
    dev.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    dev.device_address  = XGZP_ADDR;
    dev.scl_speed_hz    = 100000;
    i2c_master_bus_add_device(s_i2c_bus, &dev, &s_xgzp_dev);

    /* 逐通道探测：TCA 选通后试读一只字节，成功即该通道传感器在线 */
    for (int i = 0; i < 2; ++i) {
        s_xgzp_present[i] = false;
        if (s_tca_present && tca_select(s_xgzp_ch[i]) == 0) {
            uint8_t reg = XGZP_REG_PDATA, dummy[5] = { 0 };
            s_xgzp_present[i] =
                (i2c_master_transmit_receive(s_xgzp_dev, &reg, 1, dummy, 5, 20) == ESP_OK);
        }
    }
    tca_select(0);   /* 复位到通道 0（传感器#1） */
    printf("[HAL] tca9548a@0x70 %s, sensors CH0=%d CH1=%d\n",
           s_tca_present ? "ok" : "MISSING",
           (int)s_xgzp_present[0], (int)s_xgzp_present[1]);
}

/* TCA9548A 通道选择：向 0x70 写 1 字节 (1<<ch)（模块例程 selectPort 语义） */
static int tca_select(uint8_t ch)
{
    uint8_t cmd = (uint8_t)(1u << ch);
    return (i2c_master_transmit(s_tca_dev, &cmd, 1, 10) == ESP_OK) ? 0 : -1;
}

static int xgzp_read_kpa(uint8_t idx, float *kpa)
{
    if (!s_xgzp_present[idx]) return -1;

    /* 先切通道（传感器#1=CH0 / #2=CH1），再对 0x58 读 */
    if (s_tca_present && tca_select(s_xgzp_ch[idx]) != 0) return -1;

    /* 从 0x04 连读 5 字节：ASIC 自动刷新，无需启动/轮询（手册第 7 页读取序列） */
    uint8_t reg = XGZP_REG_PDATA, data[5] = { 0 };
    if (i2c_master_transmit_receive(s_xgzp_dev, &reg, 1, data, 5, 20) != ESP_OK)
        return -1;

    int32_t sum = ((int32_t)data[0] << 16) | ((int32_t)data[1] << 8) | data[2];
    if (sum & 0x800000) sum -= 0x1000000;      /* 24 位补码 */

    /* P[Pa] = sum / 2^21 × (PMAX−PMIN)（手册第 7 页公式） */
    *kpa = (float)sum / XGZP_TWO_POW_21 * XGZP_SPAN_PA / 1000.0f;   /* Pa → kPa */
    return 0;
}

static int pn_sensor_read(uint8_t idx, float *kpa)
{
    return xgzp_read_kpa(idx, kpa);
}

static uint32_t pn_now_ms(void) { return (uint32_t)(esp_timer_get_time() / 1000); }

/* ---------- HAL 绑定 ---------- */
static pn_hal_if_t s_if = {
    .valve_write = pn_valve_write,
    .pump_write  = pn_pump_write,
    .sensor_read = pn_sensor_read,
    .now_ms      = pn_now_ms,
};

const pn_hal_if_t *pn_hal_esp32_init(void)
{
    ledc_init_all();
    servo_init_all();
    i2c_init_all();
    return &s_if;
}
