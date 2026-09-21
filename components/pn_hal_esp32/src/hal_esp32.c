/**
 * pn_hal_esp32.c — ESP32-S3 硬件层实现
 *
 * 引脚分配（study-notes/10 第三节）：
 *   阀:  PORT1=4 PORT2=5 PORT3=6 PORT4=7 PORT5=10 INLET=11 VENT=12   (LEDC ch0-6)
 *   泵:  GPIO21                                                       (LEDC ch7)
 *   kit 舵机开关: 泵=15 充气=16 吸气=17                                (RMT ch0-2)
 *   I2C: SDA=8 SCL=9（XGZP6897D + TCA9548A）
 *
 * 铁律：阀全走 LEDC（开=255 满占空比，保持=降占空比），绝不用纯数字写。
 */
#include "pn_hal_esp32/hal_esp32.h"

#include "driver/ledc.h"
#include "driver/rmt_tx.h"
#include "driver/i2c_master.h"
#include "esp_timer.h"
#include "esp_check.h"

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

/* I2C */
static i2c_master_bus_handle_t s_i2c_bus;
static i2c_master_dev_handle_t s_xgzp_dev[2];
static bool s_xgzp_present[2];
static const uint8_t s_xgzp_addr[2] = { 0x6D, 0x5D };   /* 两只不同地址（订货配置） */

/* ---------- 阀/泵：LEDC ---------- */
static void pn_valve_write(uint8_t idx, uint8_t duty)
{
    ledc_set_duty(LEDC_LOW_SPEED_MODE, (ledc_channel_t)idx, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, (ledc_channel_t)idx);
}

static void pn_pump_write(uint8_t idx, uint8_t duty)
{
    (void)idx;   /* P0 单泵 */
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_7, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_7);
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
        ESP_ERROR_CHECK(ledc_channel_config(&ch));
    }
    ch.gpio_num = PN_PUMP_GPIO;
    ch.channel  = LEDC_CHANNEL_7;
    ESP_ERROR_CHECK(ledc_channel_config(&ch));
}

/* ---------- kit 舵机开关：RMT 50Hz ---------- */
static rmt_channel_handle_t s_servo_rmt[3];
static rmt_encoder_handle_t s_servo_enc[3];

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
    if (switch_idx >= 3) return;
    if (pulse_us < 500)  pulse_us = 500;
    if (pulse_us > 2500) pulse_us = 2500;
    static uint16_t pulses[3];
    pulses[switch_idx] = pulse_us;
    rmt_transmit_config_t cfg = { .loop_count = -1 };
    rmt_transmit(s_servo_rmt[switch_idx], s_servo_enc[switch_idx],
                 &pulses[switch_idx], sizeof(uint16_t), &cfg);
}

static void servo_init_all(void)
{
    rmt_tx_channel_config_t tx = { 0 };
    tx.clk_src           = RMT_CLK_SRC_DEFAULT;
    tx.resolution_hz     = PN_SERVO_RES_US;
    tx.mem_block_symbols = 64;
    tx.trans_queue_depth = 1;
    for (int i = 0; i < 3; ++i) {
        tx.gpio_num = s_servo_gpio[i];
        ESP_ERROR_CHECK(rmt_new_tx_channel(&tx, &s_servo_rmt[i]));

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
    i2c_master_bus_config_t bus = { 0 };
    bus.i2c_port  = I2C_NUM_0;
    bus.sda_io_num = GPIO_NUM_8;
    bus.scl_io_num = GPIO_NUM_9;
    bus.clk_source = I2C_CLK_SRC_DEFAULT;
    bus.glitch_ignore_cnt = 7;
    bus.flags.enable_internal_pullup = true;   /* P0 面包板阶段先靠内部上拉 */
    ESP_ERROR_CHECK(i2c_new_master_bus(&bus, &s_i2c_bus));

    for (int i = 0; i < 2; ++i) {
        i2c_device_config_t dev = { 0 };
        dev.dev_addr_length = I2C_ADDR_BIT_LEN_7;
        dev.device_address  = s_xgzp_addr[i];
        dev.scl_speed_hz    = 100000;
        s_xgzp_present[i] =
            (i2c_master_bus_add_device(s_i2c_bus, &dev, &s_xgzp_dev[i]) == ESP_OK);
    }
}

static int xgzp_read_kpa(uint8_t idx, float *kpa)
{
    if (!s_xgzp_present[idx]) return -1;
    /* TODO(到货后): 按 CFSensor XGZP6897D V3.2 手册读原始数据寄存器并换算。
     * 骨架期返回 -1（上层走"传感器降级不瘫痪整机"路径），量程换算标定后填充。 */
    (void)s_xgzp_dev[idx];
    (void)kpa;
    return -1;
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
