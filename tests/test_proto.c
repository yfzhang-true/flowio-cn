/** test_proto.c — 指令协议单元测试 */
#include "test_util.h"
#include "pn_core/proto.h"

static char    s_last_cmd;
static uint8_t s_last_ports, s_last_pwm;
static int     s_calls;

static void capture(char cmd, uint8_t ports, uint8_t pwm)
{
    s_last_cmd = cmd; s_last_ports = ports; s_last_pwm = pwm; ++s_calls;
}

static void setup(void)
{
    s_last_cmd = 0; s_last_ports = 0; s_last_pwm = 0; s_calls = 0;
    pn_proto_init(capture);
}

static void feed_buf(const uint8_t *buf, uint32_t n)
{
    for (uint32_t i = 0; i < n; ++i) pn_proto_feed(buf[i]);
}

static void t_frame_roundtrip(void)
{
    setup();
    uint8_t buf[5];
    CHECK(pn_proto_build(PN_CMD_INFLATE, 0b00001, 200, buf) == 5);
    CHECK(buf[0] == PN_PROTO_MAGIC);
    feed_buf(buf, 5);
    CHECK(s_calls == 1);
    CHECK(s_last_cmd == '+');
    CHECK(s_last_ports == 0b00001);
    CHECK(s_last_pwm == 200);
    CHECK(pn_proto_frames_ok() == 1);
    CHECK(pn_proto_frames_err() == 0);
}

static void t_bad_crc_dropped(void)
{
    setup();
    uint8_t buf[5];
    pn_proto_build(PN_CMD_STOP, 0b00001, 0, buf);
    buf[4] ^= 0xFF;                          /* 破坏 CRC */
    feed_buf(buf, 5);
    CHECK(s_calls == 0);
    CHECK(pn_proto_frames_err() == 1);
    /* 解析器自动重同步：坏帧后跟好帧应正常 */
    uint8_t good[5];
    pn_proto_build(PN_CMD_STATE, 0, 0, good);
    feed_buf(good, 5);
    CHECK(s_calls == 1);
}

static void t_leading_garbage_resync(void)
{
    setup();
    /* 垃圾流含假 magic（A5,99,FF,00 会组成坏帧被吃掉），后跟 1 字节间隔 + 好帧 */
    uint8_t noise[] = { 0x00, 0x13, 0xA5, 0x99, 0xFF, 0x00, 0x00 };
    feed_buf(noise, sizeof(noise));
    uint8_t good[5];
    pn_proto_build(PN_CMD_QUERY, 0b11111, 1, good);
    feed_buf(good, 5);
    CHECK(s_calls == 1);
    CHECK(s_last_cmd == '?');
    CHECK(s_last_ports == 0b11111);
}

static void t_crc_known_vector(void)
{
    /* CRC8/ATM(self-documented): 单字节 "0xA5" 的值固定，防手滑改多项式 */
    setup();
    uint8_t one[1] = { 0xA5 };
    uint8_t v = pn_proto_crc8(one, 1);
    CHECK(v == pn_proto_crc8(one, 1));       /* 确定性 */
    uint8_t buf[5];
    pn_proto_build(PN_CMD_RESET, 0, 0, buf);
    CHECK(buf[4] == pn_proto_crc8(buf, 4));  /* 自洽 */
}

void test_proto_all(void)
{
    RUN_TEST(t_frame_roundtrip);
    RUN_TEST(t_bad_crc_dropped);
    RUN_TEST(t_leading_garbage_resync);
    RUN_TEST(t_crc_known_vector);
}
