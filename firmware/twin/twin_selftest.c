/** twin_selftest.c — 数字孪生 DLL 逻辑自检（不依赖 HTTP） */
#include "twin_api.h"
#include <stdio.h>

int main(void)
{
    pn_twin_init();
    printf("init: state=0x%04X sensor0=%.2f\n", pn_twin_state(), (double)pn_twin_sensor(0));

    pn_twin_command("I 1 255");
    printf("after I 1 255: state=0x%04X valve_port1=%u pump=%u\n",
           pn_twin_state(), pn_twin_valve_duty(0), pn_twin_pump_duty());

    /* 泵转 40 tick（2 秒）：孔口模型 0→约 19 kPa（渐近 61 死点） */
    for (int i = 0; i < 40; ++i) pn_twin_tick();
    printf("after 2s pump: sensor0=%.2f kPa (期望 15~25)\n", (double)pn_twin_sensor(0));

    /* 闭环到 40kPa（P0 泵死点 61，目标可达） */
    pn_twin_command("G 1 40 0");
    int st = 0;
    for (int i = 0; i < 200 && st != 2; ++i) st = pn_twin_tick();   /* 2=PN_CL_DONE */
    printf("closed loop: status=%d sensor0=%.2f kPa (期望 ~40)\n", st, (double)pn_twin_sensor(0));

    /* 释放 4 秒：孔口排气 → 接近 0 */
    pn_twin_command("R 1");
    for (int i = 0; i < 160; ++i) pn_twin_tick();
    printf("after release 4s: sensor0=%.2f kPa (期望 <3)\n", (double)pn_twin_sensor(0));

    /* TinyML Phase 0：泄漏注入 demo——密封 50kPa 级，注入 k=0.2 观察加速衰减 */
    pn_twin_command("S 1");
    pn_twin_command("I 1 255");
    for (int i = 0; i < 60; ++i) pn_twin_tick();          /* 3s 充到 ~55 */
    pn_twin_command("S 1");
    float pl0 = pn_twin_sensor(0);
    pn_twin_set_leak(0, 0.2f);
    for (int i = 0; i < 40; ++i) pn_twin_tick();          /* 2s 泄漏 */
    float pl1 = pn_twin_sensor(0);
    printf("leak k=0.2: %.2f -> %.2f kPa in 2s (期望降 >4)\n", (double)pl0, (double)pl1);

    return 0;
}
