/**
 * pn_core/sensor_if.h — 传感器抽象接口（S4）
 *
 * 动作/闭环层统一经本接口探测与读数，不感知通道后面挂的是
 * mock XGZP、真机槽位还是未来的其他传感器型号。
 * 错误码独立于 tca_err_t：BUS/CHAN 类失败对上层一律 = 物理未连接；
 * SENS_TIMEOUT / SENS_CRC 留给真机 XGZP 字节级读取路径（S5+）使用。
 */
#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    SENSOR_NONE = 0,       /* 通道上无设备 */
    SENSOR_MOCK_XGZP,      /* 主机 mock 总线表上的模拟 XGZP（本期） */
    SENSOR_REAL_SLOT,      /* 真机槽位（探测/读数由 hal 层负责，本期只占位） */
} sensor_type_t;

typedef enum {
    SENS_OK = 0,
    SENS_DISCONNECT,       /* 总线无应答 / 通道越界 → 视为未连接 */
    SENS_TIMEOUT,          /* 预留：真机读超时 */
    SENS_CRC,              /* 预留：真机校验错 */
} sens_err_t;

/* 探测通道上的传感器型号。空通道返回 SENS_OK + SENSOR_NONE（探测语义），
 * 越界/总线错返回 SENS_DISCONNECT。 */
sens_err_t sensor_probe(uint8_t ch, sensor_type_t *out);

/* 读通道首传感器压力 Pa×10（转发 tca_read_pa，映射错误码）。 */
sens_err_t sensor_read_pa(uint8_t ch, int32_t *pa10);

#ifdef __cplusplus
}
#endif
