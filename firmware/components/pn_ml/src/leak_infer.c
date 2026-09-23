/**
 * leak_infer.c — 1D CNN int8 前向（与 TFLite 量化语义逐层一致）
 *
 * 拓扑: q_in[80] → conv(24,k7)+relu → pool4 → conv(24,k5)+relu → pool4
 *       → conv(32,k3)+relu → flatten[32] → fc(24)+relu → fc(3) → softmax
 * Conv1D 在 TFLite 中为 H=1 的 CONV_2D，权重布局 [out,1,k,in]。
 *
 * 量化语义（TFLite int8 标准，权重 zp=0 由导出脚本断言）：
 *   acc = Σ q_in·q_w − zp_in·Σ q_w + b_i32     （b_i32 的 scale = s_in·s_w）
 *   out_q = relu( clip( round(acc·s_in·s_w/s_out) + zp_out ) )
 *   int8 域 relu = clamp 下限 zp_out（real 0 ⇔ q = zp_out）
 * 池化在 int8 域直接取 max（量化单调，scale 不变）；softmax 用 float（仅 3 元）。
 */
#include "pn_ml/leak_infer.h"
#include "pn_ml/leak_model_data.h"

#include <math.h>

#define CH1 24
#define CH2 24
#define CH3 32
#define L1_OUT 74   /* 80−7+1 */
#define P1_OUT 18   /* (74−4)/4+1 */
#define L2_OUT 14   /* 18−5+1 */
#define P2_OUT 3    /* (14−4)/4+1 */
#define L3_OUT 1    /* 3−3+1 */
#define FC1_IN 32   /* = CH3×L3_OUT，导出文件亦提供 PN_ML_FLAT 交叉核对 */

static int8_t clamp8(int32_t v)
{
    if (v < -128) return -128;
    if (v > 127) return 127;
    return (int8_t)v;
}

/* requant + relu：m = s_in·s_w/s_out（调用方算好） */
static int8_t requant_relu(int32_t acc, float m, int32_t zp_out)
{
    int32_t v = (int32_t)lroundf((float)acc * m) + zp_out;
    if (v < zp_out) v = zp_out;          /* relu */
    return clamp8(v);
}

static int32_t w_colsum(const int8_t *w, int n)   /* Σq_w（单输出通道核内） */
{
    int32_t s = 0;
    for (int i = 0; i < n; ++i) s += w[i];
    return s;
}

/* 卷积（H=1 的 1D）：x[t*inch+ic]，w[oc*k*inch + j*inch + ic]，y[t*outch+oc]
 * 权重 per-channel 量化：m[oc] = s_in·s_w[oc]/s_out */
static void conv_relu(const int8_t *x, int xlen, int inch,
                      const int8_t *w, const int32_t *b, int outch, int k,
                      float s_in, const float *s_w, const pn_ml_quant_t *qo,
                      int32_t zp_in, int8_t *y)
{
    int ylen = xlen - k + 1;
    int kn = k * inch;
    for (int oc = 0; oc < outch; ++oc) {
        const int8_t *wk = w + (size_t)oc * kn;
        float m = s_in * s_w[oc] / qo->scale;
        int32_t base = b[oc] - zp_in * w_colsum(wk, kn);
        for (int t = 0; t < ylen; ++t) {
            int32_t acc = base;
            for (int j = 0; j < k; ++j) {
                const int8_t *xw = x + (size_t)(t + j) * inch;
                const int8_t *ww = wk + (size_t)j * inch;
                for (int ic = 0; ic < inch; ++ic)
                    acc += (int32_t)xw[ic] * ww[ic];
            }
            y[t * outch + oc] = requant_relu(acc, m, qo->zp);
        }
    }
}

static void pool4(const int8_t *x, int len, int ch, int8_t *y)
{
    int ylen = (len - 4) / 4 + 1;
    for (int t = 0; t < ylen; ++t)
        for (int c = 0; c < ch; ++c) {
            int8_t mx = x[(size_t)(t * 4) * ch + c];
            for (int j = 1; j < 4; ++j) {
                int8_t v = x[(size_t)(t * 4 + j) * ch + c];
                if (v > mx) mx = v;
            }
            y[t * ch + c] = mx;
        }
}

int pn_ml_infer(const float *window_kpa, float *conf)
{
    int8_t q[PN_ML_WIN];
    for (int i = 0; i < PN_ML_WIN; ++i)
        q[i] = clamp8((int32_t)lroundf(window_kpa[i] / pn_ml_q_in.scale) + pn_ml_q_in.zp);

    static int8_t l1[L1_OUT * CH1], p1[P1_OUT * CH1];
    static int8_t l2[L2_OUT * CH2], p2[P2_OUT * CH2];
    static int8_t l3[L3_OUT * CH3];

    conv_relu(q, PN_ML_WIN, 1, w_conv1, b_conv1_i32, CH1, 7,
              pn_ml_q_in.scale, pn_ml_s_w_conv1, &pn_ml_q_conv1, pn_ml_q_in.zp, l1);
    pool4(l1, L1_OUT, CH1, p1);

    conv_relu(p1, P1_OUT, CH1, w_conv2, b_conv2_i32, CH2, 5,
              pn_ml_q_conv1.scale, pn_ml_s_w_conv2, &pn_ml_q_conv2, pn_ml_q_conv1.zp, l2);
    pool4(l2, L2_OUT, CH2, p2);

    conv_relu(p2, P2_OUT, CH2, w_conv3, b_conv3_i32, CH3, 3,
              pn_ml_q_conv2.scale, pn_ml_s_w_conv3, &pn_ml_q_conv3, pn_ml_q_conv2.zp, l3);

    static int8_t f1[24];
    for (int oc = 0; oc < 24; ++oc) {
        float m = pn_ml_q_conv3.scale * pn_ml_s_w_fc1[oc] / pn_ml_q_fc1.scale;
        int32_t acc = b_fc1_i32[oc] - pn_ml_q_conv3.zp * w_colsum(w_fc1 + (size_t)oc * FC1_IN, FC1_IN);
        for (int i = 0; i < FC1_IN; ++i)
            acc += (int32_t)l3[i] * w_fc1[(size_t)oc * FC1_IN + i];
        f1[oc] = requant_relu(acc, m, pn_ml_q_fc1.zp);
    }

    float logits[PN_ML_CLASSES];
    for (int oc = 0; oc < PN_ML_CLASSES; ++oc) {
        int32_t acc = b_fc2_i32[oc] - pn_ml_q_fc1.zp * w_colsum(w_fc2 + (size_t)oc * 24, 24);
        for (int i = 0; i < 24; ++i)
            acc += (int32_t)f1[i] * w_fc2[(size_t)oc * 24 + i];
        logits[oc] = (float)acc * (pn_ml_q_fc1.scale * pn_ml_s_w_fc2[oc]);   /* real 域 logits */
    }

    float mx = logits[0];
    for (int c = 1; c < PN_ML_CLASSES; ++c) if (logits[c] > mx) mx = logits[c];
    float sum = 0.f, prob[PN_ML_CLASSES];
    for (int c = 0; c < PN_ML_CLASSES; ++c) { prob[c] = expf(logits[c] - mx); sum += prob[c]; }
    int best = 0;
    for (int c = 1; c < PN_ML_CLASSES; ++c) if (prob[c] > prob[best]) best = c;
    if (conf) *conf = prob[best] / sum;
    return best;
}

const char *pn_ml_class_name(int cls)
{
    switch (cls) {
    case 0: return "normal";
    case 1: return "leak_minor";
    case 2: return "leak_major";
    default: return "?";
    }
}
