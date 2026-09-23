/**
 * leak_model_data.h — 导出模型数据接口（leak_model_data.c 由 ml_export_c.py 生成）
 */
#ifndef PN_ML_LEAK_MODEL_DATA_H
#define PN_ML_LEAK_MODEL_DATA_H

#include <stdint.h>

typedef struct { float scale; int32_t zp; } pn_ml_quant_t;

/* 各层张量量化参数（TFLite 全 int8） */
extern const pn_ml_quant_t pn_ml_q_in;    /* 输入 kPa→int8 */
extern const pn_ml_quant_t pn_ml_q_conv1, pn_ml_q_conv2, pn_ml_q_conv3;
extern const pn_ml_quant_t pn_ml_q_fc1, pn_ml_q_fc2;
extern const pn_ml_quant_t pn_ml_q_out;   /* softmax 概率→int8 */

/* 每层权重量化 scale（per-channel，dim=0=输出通道；requant 乘子 m[oc] = s_in·s_w[oc]/s_out；
 * bias int32 scale = s_in·s_w[oc]，同为 per-channel） */
extern const float pn_ml_s_w_conv1[24];
extern const float pn_ml_s_w_conv2[24];
extern const float pn_ml_s_w_conv3[32];
extern const float pn_ml_s_w_fc1[24];
extern const float pn_ml_s_w_fc2[3];

/* 卷积核布局 [out, 1, k, in]（TFLite CONV_2D 原样）；FC 权重 [out, in]；
 * 偏置 int32（量化 scale = s_in·s_w，TFLite 约定） */
extern const int8_t w_conv1[24*1*7*1];  extern const int32_t b_conv1_i32[24];
extern const int8_t w_conv2[24*1*5*24]; extern const int32_t b_conv2_i32[24];
extern const int8_t w_conv3[32*1*3*24]; extern const int32_t b_conv3_i32[32];
extern const int8_t w_fc1[24*32];       extern const int32_t b_fc1_i32[24];
extern const int8_t w_fc2[3*24];        extern const int32_t b_fc2_i32[3];

extern const int PN_ML_FLAT;   /* conv3 输出展平维数（=fc1 输入） */

#endif
