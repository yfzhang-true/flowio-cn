/**
 * pn_core/tca9548.h — TCA9548A I2C 多路复用器纯逻辑驱动（S4）
 *
 * 分层契约（零平台依赖，主机 gcc 可测）：
 *   - 通道编码/校验/mock 总线表在本层；真机 I2C 写函数由 main 初始化时
 *     通过 tca_bind() 注入（hal 层提供 tca_hal_write），测试注入 mock/计数桩。
 *   - tca_bind(NULL) = 主机 mock 模式：select 只记录当前通道，scan/read_pa
 *     查 mock 表；真机模式（fn 非空）scan/read_pa 一律 ERR_BUS——真机探测/读数
 *     由 hal 层现有路径负责（pn_hal_esp32_i2c_scan / xgzp_read_kpa），
 *     pn_core 不直接碰字节级 I2C 读。
 *
 * 硬件背景（hal_esp32.c 头注释）：CJMCU-9548 模块默认地址 0x70（A2A1A0 拨码），
 * 通道选择 = 向 0x70 写 1 字节 (1<<ch)；写 0x00 = 全部断开（主总线直连语义）。
 * 本期传感器布局：CH0/CH1 = XGZP#1/#2，CH2-4 预留 → encode 仅认 ch<5。
 */
#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TCA_ADDR      0x70      /* TCA9548A 7 位地址（模块默认拨码） */
#define TCA_MANIFOLD  0xFF      /* 汇流管直连：断开全部下游通道 */

typedef enum {
    TCA_OK = 0,
    TCA_ERR_BUS,                /* I2C 无应答 / 通道上无挂载设备 */
    TCA_ERR_CHAN,               /* 通道号越界（>=5 且非 MANIFOLD） */
} tca_err_t;

/* 通道位编码：ch<5 → 1u<<ch；其他（含 0xFF）→ 0（非法，select 会旁路 MANIFOLD） */
uint8_t tca_encode(uint8_t ch);

/* hal 注入点：真机 = hal i2c 写（返回 0 成功）；主机 = mock 表（传 NULL） */
typedef int (*tca_i2c_write_fn)(uint8_t addr, uint8_t byte);
void tca_bind(tca_i2c_write_fn fn);

/* 选通通道：MANIFOLD→写 0x00 断全；encode==0→ERR_CHAN；
 * fn 非空→经 fn 写总线，失败→ERR_BUS；fn==NULL（mock）→记录当前通道后 OK */
tca_err_t tca_select(uint8_t ch);

/* ---------- mock 总线表（主机测试专用；真机模式下不可用） ---------- */
void tca_mock_reset(void);                          /* 清空全部挂载 */
void tca_mock_attach(uint8_t ch, uint8_t addr, int32_t pa10);  /* 通道挂设备 */

/* 扫描该通道挂载地址列表（截断到 max，n_out 报总数）。
 * 真机模式→ERR_BUS（真机扫描由 hal 层做，见头注释）。 */
tca_err_t tca_scan(uint8_t ch, uint8_t *addrs, uint8_t max, uint8_t *n_out);

/* 读该通道首传感器压力 Pa×10。空通道/真机模式→ERR_BUS。 */
tca_err_t tca_read_pa(uint8_t ch, int32_t *pa10);

#ifdef __cplusplus
}
#endif
