# twin/ — FlowIO-CN 数字孪生 + Web 控制台

启动：

```bash
"E:/Program Files/KiCad/10.0/bin/python.exe" server.py   # KPY（KiCad 自带 Python）
# → http://127.0.0.1:8000/
```

P1 板级说明：本目录含 P1 板级电气孪生（board_model）/参数化仿真（sim_engine）/3D 装配（meshes），
协议契约见 `API.md`（v1.2）与 `BLE.md`（真机 Web-Bluetooth 模式）；回板校准动线见 `firmware/BRINGUP.md`。

## 前端 v2（webapp/，2026-10-02 交付）

`/` = v2 产品爆炸视图核心（零构建 ES Modules，`webapp/` 直服）：

- **全屏 3D 产品场景**为唯一主角：装配叙事（加载 1.5s 部件散位收敛）+ 运输条爆炸滑杆（0-100%），
  材质对标 Liquid Glass（壳喷砂灰 / PCB 墨绿微金属 / 器件中性灰 + 环境反射）。
- **气流粒子与电流辉光长在产品上**：流拓扑由 `hardware/flowio-p1/enclosure/make_flows.py`
  从 pos.csv 同源生成 `webapp/flows.json`/`hotspots.json`；电流=行进虚线（阀电流驱动 uGain/uSpeed），
  气流=端口 Bezier 粒子流（duty 驱动速度，真空=琥珀色反向）。
- **仪表盘降级为辅助**：左控制抽屉（阀/泵 Apple 分段控件 → CLI）/ 右遥测抽屉（5 张 sparkline 玻璃卡，
  点卡展开 ECharts）/ 器件热点卡（点击 3D 器件）/ 仿真实验室全屏浮层 / 状态行（stale 红点/未标定黄徽）。
- `?debug` 叠 fps/粒子/延迟浮层；真机模式=顶栏「连接真机」（Web Bluetooth，0xA5 帧，`ble.js`）。
- 调试钩：`window.__t2 = {scene, flows, panels, simlab}`（test_webapp.js 全链断言经此读取渲染态）。
- 旧版 gui.html 挂 `/classic` 过渡（`/gui` 301→`/`）；API v1.2 端点零改动。

截图（`shots/v2_*.png`）：`v2_01_intro` 首屏装配 · `v2_02_explode50` 爆炸 50% ·
`v2_03_inflate`/`v2_04_silent` 充气/静默差分 · `v2_05_vacuum` 真空琥珀反向 ·
`v2_06_hotspot` U3 热点卡 · `v2_07_telemetry` 遥测抽屉 · `v2_08_simlab` 仿真浮层 ·
`v2_09_stale` 断连态 · `v2_10_recovered` 恢复态。

测试：`node test_webapp.js`（v2 全链 44 断言，需 8017 实例）+ 旧三套（test_gui/test_gui_p1/test_e2e 已挂 /classic）。
