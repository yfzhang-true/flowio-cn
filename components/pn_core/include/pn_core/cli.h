/**
 * pn_core/cli.h — 串口 CLI（平台无关）
 *
 * 同一套命令行分发同时服务两个宿主：
 *   - ESP32 目标机（main.c，阻塞 fgets + 10ms 控制任务）
 *   - 主机虚拟设备（virtual/，mock HAL，无硬件调试）
 * 延时函数由宿主注入：ESP32 注册 vTaskDelay 包装；虚拟设备注册 mock 时钟推进。
 */
#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*pn_cli_delay_fn_t)(uint32_t ms);

/* 注册延时函数（selftest 等阻塞步骤用）；不注册则不延时 */
void pn_cli_set_delay_fn(pn_cli_delay_fn_t fn);

/* 处理一行命令（\n 结尾或不带均可） */
void pn_cli_process_line(char *line);

/* 硬件自检序列：传感器检测 → 阀咔哒 → 汇流管 ΔP */
void pn_cli_selftest(void);

#ifdef __cplusplus
}
#endif
