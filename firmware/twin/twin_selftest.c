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

    /* TinyML Phase 0：泄漏注入 demo——H 诊断保压（泵侧密封+端口保持通），
     * 端口泄漏可被汇流管传感器观测（物理 v2.1：S 隔离保压下端口侧泄漏不可见） */
    pn_twin_command("S 1");
    pn_twin_command("I 1 255");
    for (int i = 0; i < 60; ++i) pn_twin_tick();          /* 3s 充到 ~55 */
    pn_twin_command("H 1");                               /* 诊断保压：端口通，泵侧封 */
    float pl0 = pn_twin_sensor(0);
    float pp0 = pn_twin_port_pressure(0);
    pn_twin_set_leak(0, 0.2f);
    for (int i = 0; i < 40; ++i) pn_twin_tick();          /* 2s 泄漏 */
    float pl1 = pn_twin_sensor(0);
    printf("leak k=0.2 (H hold): %.2f -> %.2f kPa in 2s (期望降 >4)\n", (double)pl0, (double)pl1);

    /* 端口独立节点 demo：S 隔离保压下，端口压力自身缓降、汇流管不受端口泄漏影响 */
    pn_twin_command("S 1");
    float pp1 = pn_twin_port_pressure(0);
    for (int i = 0; i < 40; ++i) pn_twin_tick();          /* 2s：端口节点独立演化 */
    float pp2 = pn_twin_port_pressure(0);
    printf("port node sealed: %.2f -> %.2f kPa in 2s (期望缓慢下降，端口泄漏继续作用)\n",
           (double)pp1, (double)pp2);
    (void)pp0;

    return 0;
}
