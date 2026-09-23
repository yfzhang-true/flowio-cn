/* ml_conformance.c — C 推理器 vs TFLite 一致性测试（编译运行即断言）
 * 断言：① 全部 N 窗类别与 TFLite 一致 ② 概率差 < 0.02（int8 量化舍入余量）
 */
#include "pn_ml/leak_infer.h"

#include <math.h>
#include <stdio.h>

#include "ml_conformance_vectors.h"

int main(void)
{
    int fail = 0;
    float max_dp = 0.f;
    for (int i = 0; i < ML_CONF_N; ++i) {
        float conf = 0.f;
        int cls = pn_ml_infer(ml_conf_x[i], &conf);
        float dp = fabsf(conf - ml_conf_p[i]);
        if (dp > max_dp) max_dp = dp;
        if (cls != ml_conf_cls[i] || dp > 0.02f) {
            printf("  ✗ #%d C=%d(%s) p=%.3f vs TFLite=%d p=%.3f Δ=%.3f\n",
                   i, cls, pn_ml_class_name(cls), (double)conf,
                   ml_conf_cls[i], (double)ml_conf_p[i], (double)dp);
            ++fail;
        }
    }
    printf("ML 一致性: %d/%d 对齐, max|Δp|=%.4f%s\n",
           ML_CONF_N - fail, ML_CONF_N, (double)max_dp,
           fail ? "  ✗ FAIL" : "  ✓ PASS");
    return fail ? 1 : 0;
}
