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

    /* 泵转 40 tick（2 秒）：一阶模型 0→约 39kPa（渐近 65 死点） */
    for (int i = 0; i < 40; ++i) pn_twin_tick();
    printf("after 2s pump: sensor0=%.2f kPa (期望 30~45)\n", (double)pn_twin_sensor(0));

    /* 闭环到 40kPa（P0 泵死点约 65，目标必须可达） */
    pn_twin_command("G 1 40 0");
    int st = 0;
    for (int i = 0; i < 200 && st != 2; ++i) st = pn_twin_tick();   /* 2=PN_CL_DONE */
    printf("closed loop: status=%d sensor0=%.2f kPa (期望 ~40)\n", st, (double)pn_twin_sensor(0));

    /* 释放 4 秒：指数排气 40→约 3kPa */
    pn_twin_command("R 1");
    for (int i = 0; i < 160; ++i) pn_twin_tick();
    printf("after release 4s: sensor0=%.2f kPa (期望 <5)\n", (double)pn_twin_sensor(0));

    return 0;
}
