/**
 * twin_api.h — 数字孪生 DLL 接口（封装 pn_core 逻辑 + mock HAL + 简化物理仿真）
 *
 * 上位机（Python/Web）通过本 DLL 驱动与真机完全相同的逻辑层。
 * 导出的每个函数都与未来真机行为一一对应——UI 换个传输层就能控真机。
 */
#pragma once

#include <stdint.h>

#ifdef _WIN32
#  define PN_TWIN_API __declspec(dllexport)
#else
#  define PN_TWIN_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

PN_TWIN_API void     pn_twin_init(void);
PN_TWIN_API uint32_t pn_twin_state(void);                 /* 32 位状态字 */
PN_TWIN_API float    pn_twin_sensor(uint8_t idx);         /* 传感器压力 kPa */
PN_TWIN_API void     pn_twin_set_sensor(uint8_t idx, float kpa);  /* 手动注入模拟压力 */
PN_TWIN_API void     pn_twin_command(const char *line);   /* 与真机相同的 CLI 命令 */
PN_TWIN_API int      pn_twin_tick(void);                  /* 50ms 仿真步：时钟+物理+闭环+节能+超压 */
PN_TWIN_API uint8_t  pn_twin_valve_duty(uint8_t idx);     /* 阀占空比（UI 亮度） */
PN_TWIN_API uint8_t  pn_twin_pump_duty(void);
PN_TWIN_API int      pn_twin_cl_status(void);             /* 闭环状态枚举 */
PN_TWIN_API void     pn_twin_advance(uint32_t ms);        /* 推进虚拟时钟 */

#ifdef __cplusplus
}
#endif
