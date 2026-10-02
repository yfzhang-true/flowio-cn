/**
 * [ARCHIVED 2026-10-02, spec §12] 原位于 components/pn_core/include/pn_core/leak_detect.h。
 * TinyML 泄漏检测全下线，随 pn_ml 资产归档；不再参与任何构建。
 *
 * leak_detect.h — 泄漏检测动作层（TinyML 推理的 pn_core 集成）
 *
 * 采样：pn_ml_tick() 挂在控制节拍里（孪生 50ms tick / 真机 10ms 任务均可），
 *       内部按 ≥45ms 间隔节流采传感器#0（汇流管）→ 80 点环形缓冲（4s@20Hz）。
 * 检测：pn_leak_detect() 用最近 80 点立即推理（同步，无状态机）。
 *       缓冲未满返回 -1（需上电后 4s 数据）。
 *
 * 三端同码：host DLL / ESP32 / QEMU——推理器 components/pn_ml 零依赖。
 */
#ifndef PN_CORE_LEAK_DETECT_H
#define PN_CORE_LEAK_DETECT_H

#include <stdint.h>

/* 挂在控制节拍：now_ms = 单调毫秒（孪生=tick 序号×50；真机=esp_timer） */
void pn_ml_tick(uint32_t now_ms);

/* 立即用最近 80 样本推理：返回 0=normal 1=leak_minor 2=leak_major，
 * -1=缓冲未满；conf 可 NULL 取置信度 */
int pn_leak_detect(float *conf);

/* 已缓存样本数（0..80），GUI 可用于"就绪"指示 */
int pn_ml_samples(void);

#endif
