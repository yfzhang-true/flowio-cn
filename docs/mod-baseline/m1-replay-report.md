# M1 确定性生成器重放对拍报告（hw/geom/flows 域挂载 · 2026-10-05）

> 基线：docs/mod-baseline/baseline.json @7885c62（M0 冻结）
> 对拍原则：迁移只做"代码搬迁 + import/路径解析改经 flowio 包定位"，生成逻辑零改动。
> 证明方式 = 同机同版本重放：**旧代码重放 ↔ 新代码重放 ↔ 仓内 committed 产物** 三方对拍。

## 一、重放矩阵（任务指定的 7 个确定性生成器）

| 生成器 | 旧侧 | 新侧 (flowio.*) | 归一化器 | 结论 |
|---|---|---|---|---|
| make_case | committed @53f8953 | flowio/geom/make_case.py | STEP: FILE_NAME 时间戳→`<TS>` | **STL 逐字节一致**（528484/397584 B）；STEP 归一化一致（仅时间戳 15 B 差） |
| make_manifold | committed @53f8953 | flowio/geom/make_manifold.py | 同上 | **STL 逐字节一致**（839584 B = baseline sha c485460be3d7）；STEP 归一化一致 |
| make_pump_module | committed @53f8953 | flowio/geom/make_pump_module.py | 同上 | **STL×3 逐字节一致**（19884/15084/44884 B）；STEP×3 归一化一致 |
| make_meshes | committed @53f8953 | flowio/geom/make_meshes.py | 无需（逐字节） | **11 产物全部逐字节一致**（含 valves.stl/tubes.stl/assembly.json 三个基线产物） |
| make_assembly | @53f8953 沙箱重放（同等输入） | flowio/geom/make_assembly.py 沙箱重放 | STEP 时间戳 | **STL 逐字节一致**（5447284 B）；STEP 归一化一致 |
| make_flows | @53f8953 沙箱重放 | flowio/flows/make_flows.py | 无需 | **flows.json + hotspots.json 双双逐字节一致**（旧↔新） |
| gen_sch | @393caac~1 沙箱 cwd 重放 + committed | flowio/hw/sch_gen.py | uuid4→`<UUID>` | **三方归一化逐字节一致**（448482 B raw，committed sha f9d15ecde811 不变） |

- make_assembly 输入 fab/flowio-p1.step 为 gitignored 按需产物（仓内无存），本次经
  `kicad-cli pcb export step` 现导（**板文件 sha 前后均为 be35ebc7cff8，只读验证**）；
  无器件模型（14 solids vs 原 500+）→ 两侧同等松开 `solid>=500` 质量门后对比，输入完全相同。
- gen_sch 的 uuid 归一化覆盖 root uuid/实例 uuid/junction/wire/label/no_connect/text 全部 uuid4 现场。

## 二、额外（超出任务清单的加固验证）

**gen_pcb（⛔ 本身禁重放，沙箱隔离验证 AST-PARTS 提取机制迁移无漂移）**：
旧 tools/gen_pcb.py ↔ 新 flowio/hw/pcb_gen.py 在各自沙箱（输出路径均封闭在 .tmp_replay/）
经 KiCad python 各生成骨架板 → uuid 归一 + 行排序指纹（KiCad 存盘按随机 KIID 排序 footprint，
顺序不稳定属工具行为）→ **指纹相等**（7589ab888fefeaa7，1026307 B）。真实板文件全程未动。

**make_bom（AST 读源路径迁移的回归）**：经新读源路径 flowio/hw/sch_gen.py 重放，
BOM 146 refs == CPL 147 refs 对拍一致，fab CSV 产物零字节改动。

## 三、产物不可变门（compare_baseline --products）

11 产物 sha256[:12] 全等（**含 .kicad_pcb / .kicad_sch / jlc.zip**）：

```
kicad_sch f9d15ecde811 | kicad_pcb be35ebc7cff8 | jlc.zip 7bd6420a76a1
manifold c485460be3d7 | pump-module 1e23604a63d7 | case-top d5344d928e86
case-bottom 1a51551d3f44 | assembly.json 0630def517d1 | flows.json 9f9b175a0076
valves.stl 1d30029a599e | tubes.stl 91fd51db5306          —— 23 ok / 0 bad
```

重放后的覆写产物一律 `git checkout --` 还原；最终 `git status` 干净（仅 gitignored 构建产物）。

## 四、测试全家桶（迁移后全量重跑）

| 层 | 结果 |
|---|---|
| flowio core（M0） | OK（errors/interfaces/TruthSource/views） |
| L1-L3 test_assembly | **30/0** |
| L4 test_assembly_freecad | **5/0** |
| L5 test_device_geom schema / all | **15/0 / 13/0** |
| test_flows | OK（16 elec + 12 air + 6 hotspots 断言） |
| device_graph | **21↔21 完美匹配** + flows 交叉校验 0 违例（新路径与旧 shim 双验证） |
| electrical_sim | 6 testfns OK |
| 场景矩阵（compare_baseline） | **12/12** 数值相等 |
| test_api（run_tests.sh 内） | 51 ✓ / 0 ✗ |
| test_gui / test_e2e | SKIP（playwright-core 本机未装，基线期即如此的环境前置，非 M1 回归） |

## 五、发现（非 M1 引入，如实记录）

1. **hotspots.json 陈旧漂移（预存在）**：仓内 hotspots.json 的 U2 盒尺寸 [4.9,3.9,1.75]
   （SOP 关键词命中）为 T3c（2922724）产物；T6-0（b4512ff）关键词改按长度降序后
   正确匹配为 TSSOP [7.8,4.4,1.1]，但 **hotspots.json 自 T3c 后从未再生成**。
   本次旧↔新重放双双输出新值（互为逐字节一致，证明迁移零漂移）；hotspots.json 不在
   11 产物基线内故 compare_baseline 不设防，test_flows 亦不断言盒尺寸。
   处置：M1 遵守"产物一字节不动"，保留仓内旧值，**建议在 M1 后单独提交一次
   `python flowio/flows/make_flows.py` 重生成并补 test_flows 尺寸断言**。
2. **case_geom 的 devices.json 加载恒走回退分支（预存在）**：`_load_device_dims/_load_pneu`
   引用 `Path` 但模块只 `import struct` → NameError 被宽 except 吞 → 常驻走内置兜底表
   （兜底值与 devices.json 当前等价，故无可见影响）。迁移逐字节原样保留该行为
   （改动即产物漂移）；修复建议随第五点重生成窗口一并处理（补 `from pathlib import Path`）。
3. **check_fab "zip↔散件逐字节一致" 检查红（预存在）**：jlc.zip 内 Gerber 为 CRLF，
   仓内散件在基线提交（7885c62）即为 LF（提交时换行归一化），行数/内容逐行相等、
   仅换行符差 → 字节级比较必红。zip 本体 sha 与基线一致（下单件不受影响）。
   M1 全程未触碰 fab 产物（git status 干净为证）；建议 check_fab 改为换行归一化后比较。
