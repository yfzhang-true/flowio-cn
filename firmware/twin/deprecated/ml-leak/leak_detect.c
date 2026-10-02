/**
 * [ARCHIVED 2026-10-02, spec §12] 原位于 components/pn_core/src/leak_detect.c。
 * TinyML 泄漏检测全下线，随 pn_ml 资产归档；不再参与任何构建。
 *
 * leak_detect.c — 20Hz 环形采样 + 泄漏推理（pn_core 动作层）
 */
#include "pn_core/leak_detect.h"
#include "pn_core/actions.h"
#include "pn_core/types.h"
#include "pn_ml/leak_infer.h"

#define WIN        80
#define TICK_MS    45          /* ≥45ms 节流：20Hz 采样（两档控制节拍通用） */

static float s_buf[WIN];
static int   s_head, s_count;
static uint32_t s_last_ms;

void pn_ml_tick(uint32_t now_ms)
{
    if (s_last_ms != 0 && now_ms - s_last_ms < TICK_MS) return;
    s_last_ms = now_ms ? now_ms : 1;
    float p;
    if (pn_read_pressure(0, &p) != PN_OK) return;   /* 传感器故障则跳过本拍 */
    s_buf[s_head] = p;
    s_head = (s_head + 1) % WIN;
    if (s_count < WIN) ++s_count;
}

int pn_ml_samples(void) { return s_count; }

int pn_leak_detect(float *conf)
{
    if (s_count < WIN) return -1;
    float ordered[WIN];
    for (int i = 0; i < WIN; ++i)               /* 环形 → 时间序（最旧在前） */
        ordered[i] = s_buf[(s_head + i) % WIN];
    return pn_ml_infer(ordered, conf);
}
