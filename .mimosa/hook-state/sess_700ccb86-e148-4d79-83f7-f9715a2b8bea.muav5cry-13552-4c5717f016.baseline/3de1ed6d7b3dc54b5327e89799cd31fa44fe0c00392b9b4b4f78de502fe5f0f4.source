/** test_actions.c — 气动动作层单元测试 */
#include "test_util.h"
#include "mock_hal.h"
#include "pn_core/actions.h"

static void setup(void)
{
    pn_mock_reset();
    pn_init(pn_mock_hal(), PN_CFG_GENERAL);
}

static void t_init_safe_state(void)
{
    setup();
    for (int i = 0; i < PN_VALVE_COUNT; ++i) CHECK(pn_mock_valve_duty[i] == 0);
    for (int i = 0; i < PN_PUMP_COUNT; ++i) CHECK(pn_mock_pump_duty[i] == 0);
    CHECK(pn_get_state() == 0);
}

static void t_inflation_sequence(void)
{
    setup();
    CHECK(pn_start_inflation(0b00001, 200) == PN_OK);
    CHECK(pn_mock_valve_duty[PN_VALVE_INLET] == 255);       /* 进气阀开 */
    CHECK(pn_mock_valve_duty[PN_VALVE_PORT1] == 255);       /* 端口1开 */
    CHECK(pn_mock_valve_duty[PN_VALVE_PORT2] == 0);
    CHECK(pn_mock_pump_duty[0] == 200);                     /* 泵按参数转速 */
    CHECK((pn_get_state() & (PN_SW_INLET | PN_SW_PORT1 | PN_SW_PUMP1)) != 0);
    CHECK(pn_mock_valve_duty[PN_VALVE_VENT] == 0);          /* 排气阀必须关着 */
}

static void t_zero_ports_ignored(void)
{
    setup();
    pn_err_t e = pn_start_inflation(0, 255);
    CHECK(e == PN_ERR_PARAM);
    CHECK(pn_get_state() == 0);
    CHECK(pn_mock_pump_duty[0] == 0);
}

static void t_release_passive(void)
{
    setup();
    pn_start_inflation(0b00001, 255);        /* 先充一点气 */
    CHECK(pn_start_release(0b00001) == PN_OK);
    CHECK(pn_mock_pump_duty[0] == 0);                       /* 泵停（被动释放） */
    CHECK(pn_mock_valve_duty[PN_VALVE_VENT] == 255);        /* 排气位通大气 */
    CHECK(pn_mock_valve_duty[PN_VALVE_PORT1] == 255);       /* 端口打开 */
    CHECK((pn_get_state() & PN_SW_INLET) == 0);             /* 进气阀关 */
}

static void t_stop_is_hold(void)
{
    setup();
    pn_start_inflation(0b00011, 255);
    pn_mock_advance_ms(100);
    CHECK(pn_stop_action(0b00011) == PN_OK);
    for (int i = 0; i < PN_VALVE_COUNT; ++i) CHECK(pn_mock_valve_duty[i] == 0);
    CHECK(pn_mock_pump_duty[0] == 0);
    CHECK((pn_get_state() & (PN_SW_PORT1 | PN_SW_PORT2 | PN_SW_INLET | PN_SW_VENT | PN_SW_PUMP1)) == 0);
}

static void t_config_gate(void)
{
    setup();
    pn_set_config(PN_CFG_INFLATION);
    CHECK(pn_start_vacuum(0b00001, 255) == PN_ERR_UNSUPPORTED);
    pn_set_config(PN_CFG_VACUUM);
    CHECK(pn_start_inflation(0b00001, 255) == PN_ERR_UNSUPPORTED);
    pn_set_config(PN_CFG_GENERAL);
    CHECK(pn_start_inflation(0b00001, 255) == PN_OK);
}

static void t_open_close_semantics(void)
{
    setup();
    pn_ports_set(0b00011);                   /* 端口1、2 开 */
    CHECK(pn_mock_valve_duty[PN_VALVE_PORT1] == 255);
    CHECK(pn_mock_valve_duty[PN_VALVE_PORT2] == 255);
    pn_ports_close(0b00001);                 /* 只关端口1 */
    CHECK(pn_mock_valve_duty[PN_VALVE_PORT1] == 0);
    CHECK(pn_mock_valve_duty[PN_VALVE_PORT2] == 255);       /* 端口2不受影响 */
    pn_ports_open(0b00001);                  /* 再开端口1 */
    CHECK(pn_mock_valve_duty[PN_VALVE_PORT1] == 255);
}

static void t_optimize_power(void)
{
    setup();
    pn_ports_open(0b00001);
    uint32_t t0 = pn_mock_time;
    pn_mock_advance_ms(600);                 /* 超过 500ms 阈值 */
    pn_optimize_power(170, 500);
    CHECK(pn_mock_last_valve_write(PN_VALVE_PORT1) == 170); /* 降到保持占空比 */
    CHECK(pn_get_state_of(0));                              /* 状态字仍算"开" */

    pn_mock_advance_ms(100);
    pn_optimize_power(170, 500);
    CHECK(pn_mock_last_valve_write(PN_VALVE_PORT1) == 170); /* 不重复降 */

    pn_ports_close(0b00001);                 /* 关阀重开应复位节能标记 */
    pn_ports_open(0b00001);
    CHECK(pn_mock_last_valve_write(PN_VALVE_PORT1) == 255); /* 重新全开 */
    (void)t0;
}

static void t_overpressure_failsafe(void)
{
    setup();
    pn_mock_sensor_kpa[0] = 55.f;
    pn_start_inflation(0b00001, 255);
    pn_mock_sensor_kpa[0] = 150.f;           /* 超过 120kPa 限值 */
    CHECK(pn_check_overpressure(120.f) != PN_OK);
    CHECK(pn_mock_valve_duty[PN_VALVE_PORT1] == 0);
    CHECK(pn_mock_valve_duty[PN_VALVE_INLET] == 0);
    CHECK(pn_mock_pump_duty[0] == 0);
    CHECK((pn_get_state() & PN_SW_ERROR) != 0);
}

static void t_valve_open_ms(void)
{
    setup();
    pn_ports_open(0b00001);
    pn_mock_advance_ms(250);
    CHECK(pn_valve_open_ms(PN_VALVE_PORT1) == 250);
    pn_ports_close(0b00001);
    CHECK(pn_valve_open_ms(PN_VALVE_PORT1) == 0);
}

void test_actions_all(void)
{
    RUN_TEST(t_init_safe_state);
    RUN_TEST(t_inflation_sequence);
    RUN_TEST(t_zero_ports_ignored);
    RUN_TEST(t_release_passive);
    RUN_TEST(t_stop_is_hold);
    RUN_TEST(t_config_gate);
    RUN_TEST(t_open_close_semantics);
    RUN_TEST(t_optimize_power);
    RUN_TEST(t_overpressure_failsafe);
    RUN_TEST(t_valve_open_ms);
}
