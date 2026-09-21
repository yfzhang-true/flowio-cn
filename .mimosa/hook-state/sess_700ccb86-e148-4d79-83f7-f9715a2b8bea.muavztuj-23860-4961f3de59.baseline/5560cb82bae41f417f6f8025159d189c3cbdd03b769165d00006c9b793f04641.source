/**
 * pn_core/proto.h — 指令协议（v1 二进制帧）
 *
 * 帧格式（5 字节）：[0xA5][cmd][ports][pwm][crc8]
 *  - cmd：ASCII 动作码（ '!'+ '-' '^' 'o' 'c' '?' 'S' 'R' 'r'），继承 FlowIO 式
 *    "字符指令+位掩码+参数"的思路（思想借鉴，实现原创），并补上状态查询——
 *    FlowIO 自己 TODO 里承认指令层无法回报状态字，我们每条指令都可回状态；
 *  - ports：端口位掩码 bit0..bit4；
 *  - pwm：占空比参数（0–255）；
 *  - crc8：多项式 0x07、初值 0x00，覆盖前 4 字节。
 *
 * 解析器为逐字节流式状态机：坏帧丢弃并自动重同步，统计成功/错误计数。
 */
#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PN_PROTO_MAGIC 0xA5

/* 动作码定义（应用层把这些映射到 pn_* 函数） */
#define PN_CMD_STOP      '!'    /* 停止/保压 */
#define PN_CMD_INFLATE   '+'    /* 充气 */
#define PN_CMD_VACUUM    '-'    /* 抽气 */
#define PN_CMD_RELEASE   '^'    /* 释放 */
#define PN_CMD_OPEN      'o'    /* 只开端口阀 */
#define PN_CMD_CLOSE     'c'    /* 只关端口阀 */
#define PN_CMD_QUERY     '?'    /* 读压力（pwm 字段=传感器号） */
#define PN_CMD_STATE     'S'    /* 回传状态字（pwm 字段忽略） */
#define PN_CMD_RESET     'R'    /* 闭环复位 */

typedef void (*pn_frame_handler_t)(char cmd, uint8_t ports, uint8_t pwm);

void     pn_proto_init(pn_frame_handler_t handler);
/* 喂一个字节：1=完整帧已派发；0=继续等；-1=CRC 错（帧已丢弃并重同步） */
int      pn_proto_feed(uint8_t byte);
uint8_t  pn_proto_crc8(const uint8_t *data, uint32_t len);
/* 构造发送帧（buf 至少 5 字节），返回帧长（5） */
uint32_t pn_proto_build(char cmd, uint8_t ports, uint8_t pwm, uint8_t *buf);
uint32_t pn_proto_frames_ok(void);
uint32_t pn_proto_frames_err(void);

#ifdef __cplusplus
}
#endif
