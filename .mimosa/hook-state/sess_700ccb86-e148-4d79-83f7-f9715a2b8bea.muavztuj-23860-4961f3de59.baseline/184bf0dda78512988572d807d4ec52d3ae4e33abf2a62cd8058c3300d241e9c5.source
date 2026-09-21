/**
 * pn_core/proto.c — 指令协议实现（流式状态机）
 */
#include "pn_core/proto.h"

#define PN_FRAME_LEN 5

typedef enum { ST_MAGIC, ST_CMD, ST_PORTS, ST_PWM, ST_CRC } pst_t;

static pn_frame_handler_t s_handler;
static pst_t   s_st   = ST_MAGIC;
static uint8_t s_buf[PN_FRAME_LEN];
static uint8_t s_pos  = 0;
static uint32_t s_ok  = 0;
static uint32_t s_err = 0;

uint8_t pn_proto_crc8(const uint8_t *data, uint32_t len)
{
    uint8_t crc = 0x00;
    for (uint32_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (uint8_t b = 0; b < 8; ++b)
            crc = (crc & 0x80u) ? (uint8_t)((crc << 1) ^ 0x07u) : (uint8_t)(crc << 1);
    }
    return crc;
}

void pn_proto_init(pn_frame_handler_t handler)
{
    s_handler = handler;
    s_st  = ST_MAGIC;
    s_pos = 0;
    s_ok  = 0;
    s_err = 0;
}

int pn_proto_feed(uint8_t byte)
{
    switch (s_st) {
    case ST_MAGIC:
        if (byte == PN_PROTO_MAGIC) { s_buf[s_pos++] = byte; s_st = ST_CMD; }
        return 0;                            /* 非 magic 直接丢弃，天然重同步 */
    case ST_CMD:
        s_buf[s_pos++] = byte; s_st = ST_PORTS; return 0;
    case ST_PORTS:
        s_buf[s_pos++] = byte; s_st = ST_PWM; return 0;
    case ST_PWM:
        s_buf[s_pos++] = byte; s_st = ST_CRC; return 0;
    case ST_CRC: {
        uint8_t crc = pn_proto_crc8(s_buf, 4);
        s_st  = ST_MAGIC;
        s_pos = 0;                       /* 两条路径都默认复位写指针 */
        if (crc != byte) {
            ++s_err;
            /* 重同步增强：缓冲内偏移 1 起若有 magic，把其后字节当作新帧开头重喂
             *（处理"垃圾紧贴真帧"的边界，深度有界不会递归失控） */
            for (int i = 1; i < 4; ++i) {
                if (s_buf[i] == PN_PROTO_MAGIC) {
                    s_buf[0] = PN_PROTO_MAGIC;
                    s_pos = 1;
                    s_st = ST_CMD;
                    for (int j = i + 1; j < 4; ++j) pn_proto_feed(s_buf[j]);
                    break;
                }
            }
            return -1;
        }
        ++s_ok;
        if (s_handler) s_handler((char)s_buf[1], s_buf[2], s_buf[3]);
        return 1;
    }
    default:
        s_st = ST_MAGIC; s_pos = 0;
        return 0;
    }
}

uint32_t pn_proto_build(char cmd, uint8_t ports, uint8_t pwm, uint8_t *buf)
{
    buf[0] = PN_PROTO_MAGIC;
    buf[1] = (uint8_t)cmd;
    buf[2] = ports;
    buf[3] = pwm;
    buf[4] = pn_proto_crc8(buf, 4);
    return PN_FRAME_LEN;
}

uint32_t pn_proto_frames_ok(void)  { return s_ok;  }
uint32_t pn_proto_frames_err(void) { return s_err; }
