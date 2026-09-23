/**
 * leak_infer.h — 泄漏检测 TinyML 推理器（纯 C int8，零依赖）
 *
 * 三端同码：ESP32 固件 / QEMU 整固件仿真 / host 孪生 DLL 共用本实现。
 * 模型与权重由 ml_export_c.py 从 int8 tflite 导出（重训后重跑导出即可换模型）。
 *
 * 输入：最近 80 个汇流管压力样本（kPa，20Hz=4s 窗口）
 * 输出：0=normal 1=leak_minor 2=leak_major + softmax 置信度
 */
#ifndef PN_ML_LEAK_INFER_H
#define PN_ML_LEAK_INFER_H

#include <stdint.h>

#define PN_ML_WIN 80        /* 输入窗口 4s × 20Hz */
#define PN_ML_CLASSES 3

/* 返回类别（0/1/2），conf 写入置信度（可传 NULL）；输入长度必须 = PN_ML_WIN */
int pn_ml_infer(const float *window_kpa, float *conf);

const char *pn_ml_class_name(int cls);

#endif
