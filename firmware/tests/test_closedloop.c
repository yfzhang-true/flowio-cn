/** test_closedloop.c — 非阻塞闭环状态机单元测试 */
#include "test_util.h"
#include "mock_hal.h"
#include "pn_core/closedloop.h"

static void setup(void)
{
    pn_mock_reset();
    pn_init(pn_mock_hal(), PN_CFG_GENERAL);
    pn_cl_reset();
}

static void t_idle_and_lifecycle(void)
{
    setup();
    CHECK(pn_inflate_to_tick() == PN_CL_IDLE);
    CHECK(pn_inflate_to_start(0b00001, 50.f, 0, 255, 5000) == PN_OK);
    CHECK(pn_cl_busy());
    CHECK(pn_mock_pump_duty[0] == 255);
}

static void t_running_until_target(void)
{
    setup();
    pn_inflate_to_start(0b00001, 50.f, 0, 255, 5000);
    pn_mock_sensor_kpa[0] = 20.f;
    CHECK(pn_inflate_to_tick() == PN_CL_RUNNING);
    CHECK(pn_mock_pump_duty[0] == 255);      /* 未达标泵继续 */
}

static void t_reach_target(void)
{
    setup();
    pn_inflate_to_start(0b00001, 50.f, 0, 255, 5000);
    pn_mock_advance_ms(1200);
    pn_mock_sensor_kpa[0] = 55.f;            /* 达标 */
    CHECK(pn_inflate_to_tick() == PN_CL_DONE);
    CHECK(pn_mock_pump_duty[0] == 0);        /* 泵停 */
    CHECK(pn_mock_valve_duty[PN_VALVE_PORT1] == 0);
    CHECK(pn_mock_valve_duty[PN_VALVE_INLET] == 0);
    pn_inflate_job_t job;
    pn_inflate_to_get_job(&job);
    CHECK(job.elapsed_ms == 1200);           /* 耗时=进气阀开启时长 */
    CHECK(job.reached_kpa == 55.f);
}

static void t_completed_idempotent(void)
{
    setup();
    pn_mock_sensor_kpa[0] = 55.f;
    pn_inflate_to_start(0b00001, 50.f, 0, 255, 5000);
    CHECK(pn_inflate_to_tick() == PN_CL_DONE);
    CHECK(pn_inflate_to_tick() == PN_CL_DONE);   /* 再 tick 仍 DONE 但不再动作 */
    CHECK(pn_inflate_to_start(0b00001, 30.f, 0, 255, 5000) == PN_ERR_BUSY); /* 未复位不许重启 */
    pn_cl_reset();
    pn_mock_sensor_kpa[0] = 0.f;
    CHECK(pn_inflate_to_start(0b00001, 50.f, 0, 255, 5000) == PN_OK);       /* 复位后可重启 */
}

static void t_timeout(void)
{
    setup();
    pn_inflate_to_start(0b00001, 50.f, 0, 255, 500);   /* 500ms 超时 */
    pn_mock_sensor_kpa[0] = 10.f;
    pn_mock_advance_ms(600);
    CHECK(pn_inflate_to_tick() == PN_CL_TIMEOUT);
    CHECK(pn_mock_pump_duty[0] == 0);                  /* 超时必须停泵 */
    CHECK(pn_mock_valve_duty[PN_VALVE_INLET] == 0);
}

static void t_sensor_error(void)
{
    setup();
    pn_inflate_to_start(0b00001, 50.f, 0, 255, 0);
    pn_mock_sensor_fail[0] = 1;
    CHECK(pn_inflate_to_tick() == PN_CL_ERR);
    CHECK(pn_mock_pump_duty[0] == 0);
    CHECK((pn_get_state() & PN_SW_ERROR) != 0);
}

static void t_ownership_conflict(void)
{
    setup();
    pn_inflate_to_start(0b00001, 50.f, 0, 255, 0);
    CHECK(pn_start_inflation(0b00010, 255) == PN_ERR_BUSY);  /* 闭环占线时拒绝新动作 */
    CHECK(pn_start_release(0b00001) == PN_ERR_BUSY);
}

void test_closedloop_all(void)
{
    RUN_TEST(t_idle_and_lifecycle);
    RUN_TEST(t_running_until_target);
    RUN_TEST(t_reach_target);
    RUN_TEST(t_completed_idempotent);
    RUN_TEST(t_timeout);
    RUN_TEST(t_sensor_error);
    RUN_TEST(t_ownership_conflict);
}
