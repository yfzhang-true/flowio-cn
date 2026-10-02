# 废弃前端归档（2026-09-21）

`/gui`（gui.html）是**唯一在用的前端**。以下历史页面已停止维护并停止路由（server.py 不再提供访问），
仅作演进过程存档保留。文件用 `git log --follow deprecated/<文件名>` 可查完整历史。

| 文件 | 是什么 | 废弃原因 |
|------|--------|---------|
| `index.html` | 2D 全动画气路页（首版数字孪生，提交 cde983d） | 功能被 gui.html 完整取代 |
| `babylon.html` | Babylon.js 3D 孪生页（提交 dc298c5） | WebGL 重、曾致 IAB 渲染全黑；3D 非当前目标 |
| `proto3d.html` | 3D+2D 混合草稿（gui.html 重写前的过渡稿） | 存在未定义引用等缺陷，已被重写取代 |

如需复用 3D 页面：`git show <历史提交>:firmware/twin/lib/babylon.min.js > babylon.min.js`
取回库文件（Babylon.js 8.14, Apache 2.0），并在 server.py 恢复对应路由。

## 仿真工具归档（2026-10-01）

`sim-legacy/`（原 `hardware/flowio-p1/tools/sim/`，git mv 保留历史）是首版四电路仿真
交付工具：run_all.py + sim_buck/dior/valve/i2c + simlib（依赖 KiCad python 的 numpy，
report(md,png) 直接落盘式 API）。已被 `firmware/twin/sim_engine.py`（纯函数
`run(circuit, params)`，真源）+ `firmware/twin/sim_export.py`（纯 stdlib SVG/md 导出，
`python sim_engine.py --export` → `firmware/twin/sim_out/`）完整取代——消除双份仿真
代码并存。旧版独有的 buck_loadstep（时变负载激励）不在新引擎参数域，等价检查由前端
重算页 iload 参数扫描覆盖；旧交付物（out/ 下 2026-10-01 报告+6 SVG）随目录一并归档。

