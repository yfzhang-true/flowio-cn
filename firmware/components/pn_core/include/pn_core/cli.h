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

/* 应答行捕获（S5 BLE resp 特征用）：每条命令的单行应答（"inflate=0" 等）
 * 在 printf 的同时转发给 sink；不注册则零开销。自检多行诊断走 printf 不进 sink。 */
typedef void (*pn_cli_resp_sink_t)(const char *line);
void pn_cli_set_resp_sink(pn_cli_resp_sink_t fn);

/* 硬件自检序列：传感器检测 → 阀咔哒 → 汇流管 ΔP */
void pn_cli_selftest(void);

#ifdef __cplusplus
}
#endif
