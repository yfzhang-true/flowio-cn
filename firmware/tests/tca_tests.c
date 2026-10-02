/** tca_tests.c — TCA9548A 纯逻辑驱动 + sensor_if 抽象单元测试（S4）
 *
 * 覆盖：encode 边界 / MANIFOLD 旁路 / mock 总线表 attach+scan+read /
 *       空通道→ERR_BUS / 通道越界→ERR_CHAN / 真机 fn 绑定后 select 计数 /
 *       sensor_if 错误码映射（TCA_ERR_*→SENS_*）
 */
#include "test_util.h"
#include "pn_core/tca9548.h"
#include "pn_core/sensor_if.h"

/* ---------- encode：位编码契约 ---------- */
static void t_encode_basics(void)
{
    tca_bind(NULL);                    /* 每用例复位到主机 mock 模式 */
    tca_mock_reset();
    CHECK(tca_encode(0) == 0x01);
    CHECK(tca_encode(1) == 0x02);
    CHECK(tca_encode(4) == 0x10);
    CHECK(tca_encode(5) == 0x00);      /* 本期只接 5 通道（CH0-4） */
    CHECK(tca_encode(7) == 0x00);
}

/* ---------- MANIFOLD：0xFF 旁路 encode，写 0 断全通道 ---------- */
static void t_manifold_bypass(void)
{
    tca_bind(NULL);
    tca_mock_reset();
    CHECK(tca_select(TCA_MANIFOLD) == TCA_OK);       /* 0xFF 不走 encode（其值本为 0） */
    /* 断全后各通道仍可在 mock 表上重新选通 */
    tca_mock_attach(0, 0x58, 100);
    CHECK(tca_select(0) == TCA_OK);
}

/* ---------- mock 总线表：attach + read 值契约 ---------- */
static void t_mock_attach_read_ok(void)
{
    tca_bind(NULL);
    tca_mock_reset();
    tca_mock_attach(0, 0x58, 1234);
    tca_mock_attach(1, 0x58, -567);                  /* 负压（抽气）也要无损 */
    int32_t pa = 0;
    CHECK(tca_read_pa(0, &pa) == TCA_OK);
    CHECK(pa == 1234);
    CHECK(tca_read_pa(1, &pa) == TCA_OK);
    CHECK(pa == -567);
}

/* ---------- 空通道：read → ERR_BUS（无挂载视为总线无应答） ---------- */
static void t_empty_channel_read_err(void)
{
    tca_bind(NULL);
    tca_mock_reset();
    tca_mock_attach(0, 0x58, 42);
    int32_t pa = 0;
    CHECK(tca_read_pa(1, &pa) == TCA_ERR_BUS);       /* CH1 空 */
    CHECK(tca_read_pa(3, &pa) == TCA_ERR_BUS);       /* CH3 空 */
    CHECK(tca_read_pa(0, &pa) == TCA_OK);            /* CH1 失败不影响 CH0 */
    CHECK(pa == 42);
}

/* ---------- scan：两地址挂载 n_out=2 ---------- */
static void t_scan_two_addrs(void)
{
    tca_bind(NULL);
    tca_mock_reset();
    tca_mock_attach(2, 0x58, 10);
    tca_mock_attach(2, 0x5D, 20);
    uint8_t addrs[8] = { 0 };
    uint8_t n = 0xFF;
    CHECK(tca_scan(2, addrs, 8, &n) == TCA_OK);
    CHECK(n == 2);
    CHECK(addrs[0] == 0x58);
    CHECK(addrs[1] == 0x5D);
    /* 空通道 scan：OK 且 n_out=0（探测语义：无挂载不是错误） */
    CHECK(tca_scan(4, addrs, 8, &n) == TCA_OK);
    CHECK(n == 0);
    /* max 截断：缓冲 1 只回填首个，n_out 仍报总数 2 */
    CHECK(tca_scan(2, addrs, 1, &n) == TCA_OK);
    CHECK(n == 2);
    CHECK(addrs[0] == 0x58);
}

/* ---------- 通道越界 → ERR_CHAN ---------- */
static void t_ch_out_of_range(void)
{
    tca_bind(NULL);
    tca_mock_reset();
    CHECK(tca_select(7) == TCA_ERR_CHAN);
    CHECK(tca_select(200) == TCA_ERR_CHAN);
    uint8_t n = 0;
    CHECK(tca_scan(7, NULL, 0, &n) == TCA_ERR_CHAN);
    int32_t pa = 0;
    CHECK(tca_read_pa(5, &pa) == TCA_ERR_CHAN);
}

/* ---------- 真机 fn 绑定：select 成功计数 + fn 报错→ERR_BUS ---------- */
static int  s_fn_calls;
static uint8_t s_fn_last_addr, s_fn_last_byte;
static int s_fn_fail;

static int counting_fn(uint8_t addr, uint8_t byte)
{
    ++s_fn_calls; s_fn_last_addr = addr; s_fn_last_byte = byte;
    return s_fn_fail ? -1 : 0;
}

static void t_real_fn_select(void)
{
    s_fn_calls = 0; s_fn_fail = 0; s_fn_last_addr = 0; s_fn_last_byte = 0;
    tca_bind(counting_fn);                           /* 模拟真机 hal 注入 */
    CHECK(tca_select(3) == TCA_OK);
    CHECK(s_fn_calls == 1);
    CHECK(s_fn_last_addr == TCA_ADDR);
    CHECK(s_fn_last_byte == 0x08);                   /* 1<<3 */
    CHECK(tca_select(TCA_MANIFOLD) == TCA_OK);       /* 断全：写 0x00 */
    CHECK(s_fn_calls == 2);
    CHECK(s_fn_last_byte == 0x00);
    s_fn_fail = 1;                                   /* I2C NACK */
    CHECK(tca_select(0) == TCA_ERR_BUS);
    /* 真机模式 scan/read 由 hal 层负责，pn_core 一律 ERR_BUS */
    uint8_t n = 0;
    CHECK(tca_scan(0, NULL, 0, &n) == TCA_ERR_BUS);
    int32_t pa = 0;
    CHECK(tca_read_pa(0, &pa) == TCA_ERR_BUS);
    tca_bind(NULL);                                  /* 还原，避免污染后续用例 */
}

/* ---------- sensor_if：错误码映射契约 ---------- */
static void t_sensor_if_mapping(void)
{
    tca_bind(NULL);
    tca_mock_reset();
    tca_mock_attach(0, 0x58, 987);                   /* 98.7Pa */
    sensor_type_t type = SENSOR_REAL_SLOT;           /* 哨兵初值 */
    CHECK(sensor_probe(0, &type) == SENS_OK);
    CHECK(type == SENSOR_MOCK_XGZP);
    CHECK(sensor_probe(4, &type) == SENS_OK);        /* 空通道=无传感器 */
    CHECK(type == SENSOR_NONE);
    CHECK(sensor_probe(7, &type) == SENS_DISCONNECT);/* 越界→ERR_CHAN→DISCONNECT */
    int32_t pa = 0;
    CHECK(sensor_read_pa(0, &pa) == SENS_OK);
    CHECK(pa == 987);
    CHECK(sensor_read_pa(2, &pa) == SENS_DISCONNECT);/* 空通道→ERR_BUS→DISCONNECT */
    CHECK(sensor_read_pa(9, &pa) == SENS_DISCONNECT);/* 越界同上 */
}

void test_tca_all(void)
{
    RUN_TEST(t_encode_basics);
    RUN_TEST(t_manifold_bypass);
    RUN_TEST(t_mock_attach_read_ok);
    RUN_TEST(t_empty_channel_read_err);
    RUN_TEST(t_scan_two_addrs);
    RUN_TEST(t_ch_out_of_range);
    RUN_TEST(t_real_fn_select);
    RUN_TEST(t_sensor_if_mapping);
}
