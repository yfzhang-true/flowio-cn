# 书稿 × 仓库真源 一致性审计报告（AUDIT）

> 日期：2026-10-01 · 审计员：独立一致性审计代理（只报告，不改代码/书稿）
> 范围：`book/content/*.tex` 全 14 文件 vs 仓库真源（spec `2026-10-03-book-code-consistency-design.md` §1 映射表）
> 方法：① 复跑 `book/tools/consistency_check.py`（13 条 findings 逐条人工复核真伪与归类）；
> ② 重点语义专项逐章人工比对（关断续流物理 / CLI 实表 / BLE 契约 / webapp 实现 / SDK 签名 / 工单数字 / 路线图 / 费用口径）；
> ③ 可执行验证：主机 33 测试实跑、CRC 全锚点重算、tickets report 实跑、git 提交链核对、BOM/断言逐数清点。

---

## 0. 总计

| 分级 | 数量 | 明细 |
|---|---|---|
| **Critical** | 2 | ① ch12-product 为 11 行骨架且路线图与 HANDOFF 五项不符；② **仓库 bug**：qemu_smoke.sh 第 7 项期望串过期（TinyML 下线未同步），A105"九项全过"当前不可复现 |
| **Important** | 1 | ch00a"6 路 XGZP6897D **并行**采样"（实现为 TCA9548A **分时**、P0 实装 PN_SENSOR_COUNT=2） |
| **Minor** | 13 | encode 签名注解、/api/time 方法、呼吸周期 4s、缓动令牌表述、BRINGUP 30→36、api.sh 50→43、test_flows.py 位置、resp"环形缓冲"、G 命令 `<s>` 记号、两处文件名简写、ESP32S3DS 孤立 cite、"十二章"计数、`<s>`（含第 2 项）等，见 §2/§3 |
| 机器 findings 复核 | 13 条 | 真 1（ch10 encode 签名，Minor）；伪/检查器映射 12（声明省略、排版合并、章映射过期、简写歧义） |
| 仓库侧问题 | 3 | 1 Critical（qemu 期望串）+ 2 Minor（呼吸周期实现、HANDOFF"README 已改"不实），见 §4 |

---

## 1. 逐章审计表（14 行）

✅=与真源一致（含已声明的省略/摘编） · ⚠️=有 Minor/Important 漂移 · ❌=有 Critical 缺失或漂移

| 章（文件） | 检查项 | 结论 | 证据（真源侧） | 处置建议（改书稿具体成什么） |
|---|---|---|---|---|
| 1 理论·DT（ch00a-dt-theory.tex） | 文献真实性（Tao2019/AMiner）；文献台账数字；技术栈表 | ⚠️ | AMiner 检索 Tao2019=IEEE TII 2019（被引 1001–5000 档，书称"逾 4600"相容）；literature/ 根目录 .txt 伴生恰 15、citers/ 81——书"15 精读+81 被引"逐数符合；**但 L73"6 路 XGZP6897D 并行采样"**：types.h L21 `PN_SENSOR_COUNT 2`，且 I2C 经 TCA9548A 分时选通（ch02 表"单传感器分时"），"并行"不成立（6=1 汇流管+5 XH 座仅为设计容量，gen_sch.py L344 `range(5)`） | L73 改为"**双路 XGZP6897D 经 TCA9548A 分时采样（汇流管+端口侧，可扩 5 端口座）**"；"本书十二章/后面十章"表述与 14 个印张章的映射加一句说明（理论篇 2 章不计入"十二章"） |
| 2 理论·气动（ch00b-pneumatic-theory.tex） | γ=1.2、ANSI 114.5、临界压比 1.893、RC r²=0.983 与文献/twin 三方一致 | ✅ | ch02 表 tab:twin-lit 与 sim/twin_api 常数同源；机器 equation 锚点"114.5"通过；Xavier 2022 DOI 10.3389/frobt.2022.818187 与 bib 一致 | 无 |
| 3 生态位（ch01-intro.tex） | 定价 300–500；36 工单；十二章地图；文献台账 | ✅ | 12 章地图表与 content/ 文件一一对应；"15 精读/81 citers"实测相等；"每口传感"为设计定位（P0 实装 2 只在 ch08 已注明），无矛盾 | 可选：在差异化四件套处注一句"P0 先装 2 只（slot2–4 预留）" |
| 4 孪生先行（ch02-twin.tex） | **关断续流物理**；v33 口径；参数表；API v1.2 表；泄漏下线叙事 | ✅（2 Minor） | L208"开通 τ≈1.78ms / 关断 SS14 续流 τ=L/r_coil≈1.79ms、负稳态过零钳位"= board_model.py L74–85 **逐条一致（非对称，未写成对称旧版）**；3.269=vout3v3 [实测]（L218）与 BOARD_PARAMS L33 一致，"双源 3.269/3.2638"修复叙事在 ch09 与 telemetry() 注释吻合；API 表 7 端点中 6 个与 server.py 完全一致，**"GET/POST /api/time" 实为 POST-only**（server.py L14/L318 均在 do_POST）；'L'退化为 leak=off 与 cli.c L133–135 一致 | tab:twin-apis"/api/time"行改"**POST /api/time**"；popcount 列表可恢复 `(float)__builtin_popcount` 原样（见 §2-F8） |
| 5 原理图（ch03-schematic.tex） | 行号锚点 #9/#11/#12；13 修正表；GPIO/器件计数 | ✅ | gen_sch.py：SS34_C8678 D1/D2=L219/L222、D3=L245（书 L215–228/L245–246 ✓）；R324K R5=**L249** ✓；CH340K U4=L263 ✓；commit 086e789"135器件/101网络/344连接/ERC 0"逐字在 git log；阀 GPIO 4/5/6/7/10/11/12/21 = hal_esp32.c L39–42 ✓；修正 #9/#11/#12/#13 抽查与 spec §9 一致 | 无 |
| 6 PCB（ch04-pcb.tex） | DRC 146→17→6→0；提交链；几何修正数字 | ✅ | git log 逐一核实：41e697e（146）、c3337a3（146→17 零短路）、d549f4a（clearance 3→2）、cd47167（HD (77,62)→(68,65)，hole 6→1、dangling 2→1）、a38172a（17→6）、d0eb1b2（6→0）、fa2f138（终版包+hole clr 0.20）——与书全部吻合 | 无 |
| 7 制造（ch05-manufacturing.tex） | 费用双口径；BOM 38/123；via-in-pad×8；make_bom 摘编 | ✅（1 Minor） | README-jlc-order §3 合计 550–1150（全贴 5 片）、HANDOFF L191 360–720（板 5 装 2）——书 tab:fab-cost 两口径并列且各自标明出处，**现行执行口径 360–720 单一**（ch05 小结同）；BOM 实测 38 行/123 位号、pos 123 ✓；assembly-top.pdf 与 assembly-bottom.pdf 均存在 | tab:fab-files 首行 `\texttt{assembly-top/bottom.pdf}` 改为"\texttt{assembly-top.pdf} / \texttt{assembly-bottom.pdf}"（消除"路径"歧义，机器 finding P1） |
| 8 结构（ch06-enclosure.tex） | HD(68,65)；坐标映射证伪；爆炸位移；flows/hotspots 同源 | ✅（1 Minor） | make_meshes.py verify_mapping L91–102 与书逐行一致（书省略逐器 print、加一行注释）；ST 四柱 (68,65) ✓；flows.json elec=12/air=8 实测 ✓ | lst:mesh-verify 处补"……（略一行逐器打印）……"省略标记；L207 `\texttt{flows/hotspots.json}` 改"\texttt{flows.json} 与 \texttt{hotspots.json}"（机器 finding P2） |
| 9 固件（ch07-firmware.tex） | **CLI 实表逐条**；L=off 文案；33 测试；状态字位；LED 五模式 | ✅（2 Minor） | cli.c 实表 I/V/R/S/H/O/C/G/X/F/P/T/L + main.c L48–54 W（I2C 扫描）/M（舵机）——书表 13 行**全部有实现，无未实现命令（不存在 N 命令，书亦未列）**；'L' 应答"leak=off (TinyML retired 2026-10-02)"与 cli.c L135 **逐字相同**；主机 33 测试实跑"33 tests, 0 failed" ✓（分布 10/7/4/8/4 ✓）；状态字 bit0–4/5/6/7/9/15 = types.h L28–38 ✓；LED 五模式=hal_esp32.c L460–469 ✓；pn_cmd_feed/tca9548 列表机器匹配 | ① tab:fw-cli 的 `G <ports> <kPa> <s>` 第三参实为**传感器号**（cli.c L112–114 `sensor`），改"G \<ports\> \<kPa\> \<sensor\>"防误读为秒；② "十三条"按行计（O/C 一行两命令，实现 14 个字母），可加脚注 |
| 10 BLE（ch08-ble.tex） | UUID/四服务表；翻译表；20B 帧；**gui v1 残留**；线程模型 | ✅（1 Minor） | BLE.md §2–§8 逐项对照：基址 f10a5c00-…、后缀 0001–0009、属性、pwm_params 4B/255/170/500、EB FD 向量、0x8000 哨兵、保留字节校验、广播名 FLOWIO-P1-XXXX、队列深 8（ble_twin.c L444 `xQueueCreate(8,…)`）、六步 BRINGUP——全部一致；ble.js frameForLine 对 H/G/F 返回 null ✓；书中无 gui.html v1 旧描述（v1 仅以 /classic 过渡版出现，server.py L146 ✓） | L40"存入 64 字节**环形**缓冲"改"存入 64 字节**行缓冲**（最近一条应答）"——ble_twin.c L123 `s_resp_line[64]` 为单行存储，非环形 |
| 11 前端（ch09-host.tex） | **webapp 实现细节**（200ms/since/双模 sendCmd/粒子/增益）；**sim 旧路径残留**；τ 审查故事 | ✅（2 Minor） | telemetry.js L2/L98：200ms 交替轮询 ✓；`since` 去重边界点（L18/L72，server L176 `t>=since`）✓；命令双模=ble.js L135"优先 0xA5 帧，不可帧化走 ASCII 行" ✓；flows.js N_PART=50、8×50=400≤500 ✓；flows.json 12 电路+8 气弧 ✓；make_flows.py 与 fab/flowio-p1-pos.csv 路径均在（hardware/flowio-p1/enclosure/ 与 /fab/）——**无失效旧路径**；关断续流 τ 审查叙事=board_model.py 注释逐条对应 ✓；Three.js vendor REVISION 160（"r16x"）✓ | ① L17"呼吸悬浮（振幅 0.3mm、周期 4s）"：scene.js L202 `Math.sin(t/4)*0.3` 实际周期≈25.1s——**改书稿为"周期≈25s"或（更优）开修复任务把实现改为 sin(2π·t/4)**（见 §4-2）；② L17"全局缓动曲线 cubic-bezier(0.22,1,0.36,1)"是 v2 设计 spec 的令牌（spec L33/L74），实现装配动画用 easeOutQuint（scene.js L9），webapp 内无该 bezier——改为"设计令牌 spec 规定 cubic-bezier(0.22,1,0.36,1)，装配叙事实现取同族 easeOutQuint" |
| 12 SDK（ch10-sdk.tex） | **encode 签名**；vectors 8 组；CRC 锚点；client API 表；hello_glove 文件名 | ✅（1 Minor 真漂移） | **encode 签名漂移属实**：书 L48 `def encode(cmd, ports…)` 缺源码 L85 的 `cmd: _t.Union[str, int]` 注解（书 caption 称"全文摘录"）；其余全部复核通过：crc8/encode 函数体逐行一致；8 组黄金帧与 tests/vectors.json **逐字节相同**；CRC 锚点重算——"123456789"→0xF4 ✓、0xA5→0x72 ✓、A5 2B 01 C8→0x7D ✓、草案 LSB 算法→0xB1 ✓、停帧→0x8C ✓；client.py 八方法签名（含 vacuum(pwm, ports) 参数序）✓；examples/hello_glove.py 存在且全文一致（仅空行差异） | L48 签名补注解：`def encode(cmd: _t.Union[str, int], ports: int = 0, pwm: int = 0) -> bytes:`（或改用 `Union[str, int]` 并在导言说明） |
| 13 验收（ch11-acceptance.tex） | **工单数字 36/6pass/30pending**；44 断言；28/40/43；A105 九项 | ⚠️（3 Minor） | `ticket.py report` 实跑输出与书摘**逐字一致**："合计 36 张（sw 6 / hw 24 / cal 6）：pass 6 · pending 30 · fail 0 · waived 0"；tickets/ 实测 36 yaml（phase sw6/hw24/cal6）✓；test_webapp.js T() 调用 44 ✓；test_gui/p1/e2e 28/40/43 ✓（29−1/41−1/44−1 定义行）；33 测试 ✓；test_protocol 9 用例 ✓；shots v2_01–v2_10 与 book/figures 拷贝齐全 ✓；端口 8000=server.py 默认 ✓ | ① L217"BRINGUP 的 **30 个** checkbox"：BRINGUP.md 实测 **36** 个未勾项（设计 spec 成文时为 30，后 BRINGUP 扩充）——改为"BRINGUP 的 36 个 checkbox（工单生成时为 30）"或"全部 checkbox"；② L9"test\_api.sh/test\_api\_board.sh（**50 项**+板级全 OK）"：test_api.sh 实测 **43** 个 `ok` 断言、board 另约 11 项——改为"43 项 + 板级 11 项（合计 54）"或复核后写实数；③ L9"Python 侧 …test\_flows.py"：该文件在 `hardware/flowio-p1/enclosure/`，不在 firmware/twin——补注路径 |
| 14 产品化（ch12-product.tex） | **路线图五项 vs HANDOFF**；前向引用完整性 | ❌ | 全章仅 11 行骨架。HANDOFF L135/L150 遗留路线图五项=**OTA 升级、Web API 多设备同步、SDK BLE 传输（ble.py+bleak）、真机-孪生 HIL 对拍、治疗报表产品化**；书 L11 路线图写的是"更多执行器通道、无线同步、批量产线标定工装、供应链收敛"——**五项无一对应**；且 ch02 L4"数字孪生精度报告（第 product 章）"、ch02 L296、ch11 多处"详见第 product 章"均指向空章 | 按 HANDOFF 五项重写 §14.3 路线图（OTA / 多设备同步 / SDK BLE 传输 / HIL 对拍 / 报表产品化，逐项一句现状与门槛）；按 ch02 L296 承诺补"Phase CAL 六张叠图→精度报告"一节实质内容；A301–A306 六维度（阀电流/电源效率/温升/充气升压/真空死点/闭环精度）应在本章展开 |

---

## 2. 机器 findings（13 条）复核表

复跑 `consistency_check.py`：const=2, path=4, cite=1, snippet=6，合计 13。逐条裁决：

| # | 类别 | finding | 真伪 | 归类 | 复核依据 |
|---|---|---|---|---|---|
| F1 | const | valve_gpio（4/5/6/7/10/11/12/21）未在 ch07 出现 | **伪（值对、章映射错）** | **改检查器映射**（ch07→ch03） | 值在 ch03-schematic.tex L11"阀 GPIO 分配为 4/5/6/7/10/11/12/21"，与 hal_esp32.c L39–42（4,5,6,7,10,11,12+泵21）完全一致 |
| F2 | const | explode_disp=10 指向 ch13*.tex 不存在 | **伪（计划旧章号）** | **改检查器映射**（ch13→ch11） | 检查器注释自认"计划原文指向 ch13（现书稿无此章）"；值"10"实际在 ch11 L30/L122（"部件位移>10mm"）。spec §1 现行映射：13 验收→ch11 |
| F3 | path | `assembly-top/bottom.pdf` 不存在 | **伪（简写歧义）** | **改书稿**（写全两个文件名） | 实际文件 assembly-top.pdf、assembly-bottom.pdf 均在 hardware/flowio-p1/fab/；书意为"二选一"式简写，被解析为路径 |
| F4 | path | `flows/hotspots.json` 不存在 | **伪（简写歧义）** | **改书稿**（写全两个文件名） | firmware/twin/webapp/flows.json 与 hotspots.json 均存在；ch06 L207 简写所致 |
| F5 | path | `pn_core/cli.c` 不存在 | **真（简写层级缺段）** | **改书稿** | 实际路径 firmware/components/pn_core/src/cli.c；ch07 L90 简写少 `src/` 段（spec §2-4 明示路径须含 src） |
| F6 | path | `pn_core/ble_frame.c` 不存在 | **真（简写层级缺段）** | **改书稿** | 实际路径 firmware/components/pn_core/src/ble_frame.c；ch08 L101 同上 |
| F7 | cite | bib 孤立键 ESP32S3DS | **真** | **改书稿（补 cite）或删键** | reference.bib L177 有 @misc{ESP32S3DS}，全 14 章无 \cite。建议在 ch03 L9（"以 ESP32-S3-DevKitC-1 官方原理图为 baseline"）或 ch07 补 `\cite{ESP32S3DS}`；否则删键 |
| F8 | snippet | ch02 dP/dt 块漂移（缺 3 行：`(float)__builtin_popcount`、密封 early-branch、SEAL_LEAK 行） | **伪（声明省略+等价化简）** | 改检查器（容差）或书稿恢复原样 | 书 L103 有"……泄漏项……"省略号声明，`p -= p*SEAL_LEAK_PER_S*dt` 属被省略的泄漏块（twin_api.c L178，物理在参数表 0.01/s 行已给）；书 L83 `popcount(ports)` 为 `(float)__builtin_popcount(ports)` 的化简；书 L97 `f = P_ATM_KPA*d` 与源三元式数学等价（三支同值）。**无语义漂移** |
| F9 | snippet | ch02 BOARD_PARAMS 缺 `"mos": 350.0,` | **伪（排版合并）** | 改检查器（容忍行合并） | 书把 theta 字典并为一行 `"theta": {"cpu": 35.0, "buck": 130.0, "mos": 350.0}`，子串因行尾逗号→`}` 差一字未命中；数值 350 与源 L39 一致 |
| F10 | snippet | ch05 make_bom 缺 6 行 | **伪（合法摘编）** | 改检查器（白名单）或忽略 | 书 caption 明写"**（摘编）**"；mpn_of 两行合并为等价单行链式调用；省略的 noplace 行在正文 L146"无码器件……明确打印不入 BOM"已覆盖语义 |
| F11 | snippet | ch06 verify_mapping 缺 3 行 | **伪（轻微）** | 改书稿（加省略标记）或忽略 | 书省略逐器 print 行（make_meshes.py L99–100）、并把末行 print 拆两行、加一行解释性注释；逻辑逐行一致（含 0.01 容差、三锚点、'-PosY+75' rejected 文案） |
| F12 | snippet | ch09 tau 块缺 2 行（i_inf、for k…） | **伪（合法省略）** | 改检查器（容忍 `...`） | 书 L86 有 `...` 省略号；被省的 `i_inf = vbus/(r_coil+rds)` 在正文 L77 以公式给出（I∞=5V/14.04Ω≈0.356A）——**关断续流非对称物理在书稿中正确**（本次专项重点结论） |
| F13 | snippet | ch10 encode 缺 1 行（签名注解） | **真（唯一真 snippet 漂移）** | **改书稿** | 书 caption"全文摘录"但 `cmd` 参数丢了 `_t.Union[str, int]` 注解；行为无差，签名表述与源不符（spec §2-3：SDK 方法签名须一致） |

小结：**13 条中仅 F13（及 F5/F6 的层级简写）为书稿侧应改项**；F1/F2 为检查器映射过期；其余为声明省略/排版合并/简写歧义造成的误报。

---

## 3. 重点语义专项结论（用户点名项）

1. **ch02/ch09 关断续流物理**：✅ 书稿两处均按非对称模型写（τ_on=L/(r_coil+rds)≈1.78ms；τ_off=L/r_coil≈1.79ms；目标负稳态 −V_F/r_coil；过零被二极管反向截止钳位），与 board_model.py L74–85 及其头注释、test_board_model 锚点一致，**未**退化为"对称衰减旧版"；ch09 的"τ 审查故事"与源码注释逐条对应。
2. **v33 双源口径（3.269 vs 3.2638）**：✅ 口径已统一且书稿如实：3.269=BOARD_PARAMS `vout3v3` 标称（v_nom），轨压现值按 vout3v3−load_reg×LOGIC_A≈3.2638 重算，telemetry()/step() 同式（board_model.py L126、L154–156 注释自证修复）；ch02 表给标称 3.269、ch09 讲修复故事——两章无互相矛盾。
3. **ch07 CLI 实表**：✅ 书表 13 行命令全部有实现（I/V/R/S/H/O/C/G/X/F/P/T 在 cli.c，W/M 在 main.c L48–54；N 命令不存在、书亦未列——无"书列未实现命令"漂移）；'L'=off 文案逐字一致。仅 G 第三参记号 `<s>` 有歧义（实为 sensor 序号）。
4. **ch08 BLE 契约**：✅ UUID 基址/九后缀/四服务表/翻译表/20B 帧例（EB FD）/哨兵/保留字节/队列深 8/64B resp/广播名/配对/NVS/六步 BRINGUP 与 BLE.md 及 ble_twin.c 一致；书未残留 gui.html v1 细节（v1 只作 /classic 过渡版被提及，与 server.py 相符）。
5. **ch09 webapp**：✅ 200ms 双源交替、since 游标语义、sendCmd 帧优先/ASCII 降级、uGain/uSpeed 映射、粒子 50/400/500、flows 12+8、make_flows→fab/pos.csv 同源链、Three r160；⚠️ 两处 Minor（呼吸周期 4s vs 实测≈25s；bezier 设计令牌被写成实现），无 hardware/ 旧路径残留。
6. **ch10 SDK**：✅ 方法签名表（含 vacuum 参数序）、8 组向量、CRC 四锚点（0xF4/0x72/0x7D/0xB1/0x8C）全部重算吻合；hello_glove.py 文件名与路径正确；❗encode 签名缺类型注解（F13，改书稿）。
7. **ch11/ch12 工单与路线图**：✅ 36 张（sw6/hw24/cal6）、pass 6、pending 30 与 `ticket.py report` 实跑逐字一致；⚠️ "BRINGUP 30 个 checkbox"现为 36、"api.sh 50 项"实测 43；❌ ch12 路线图与 HANDOFF 五项全部不符（见 §1 第 14 行）。
8. **全书费用口径**：✅ 单一——现行执行口径 360–720 元（板 5 装 2，HANDOFF L191）仅在 ch05 出现且与 550–1150（README 全贴 5 片）双口径并列、各自标明出处，其余各章无第三种口径。
9. **"5 片装 2"表述**：✅ 一致——ch05"板 5 装 2"与 ch11"制板 5 片、贴装 2 片（主力+备用）"、HANDOFF"板 5 片+贴装仅 2 片"同一口径。

---

## 4. 仓库侧问题清单（交用户裁决是否修；本审计未改任何代码）

| # | 级别 | 位置 | 问题 | 建议修法 |
|---|---|---|---|---|
| B1 | **Critical** | `firmware/qemu_smoke.sh` L52 | 第 7 项 grep 期望 `"leak=detecting samples=0/80"`，但 TinyML 2026-10-02 下线后 cli.c L135 只应答 `"leak=off (TinyML retired 2026-10-02)"` → **冒烟第 7 项必失败（8/9），ch07"九项全过才算冒烟通过"与 ch11 A105 pass 当前不可复现**（L37 启动探测 grep "leak=" 仍可命中，故仅第 7 项挂） | 期望串改为 `leak=off`，复跑九项全绿后在 A107/A105 工单补一次复验记录；书稿文字（"L 路由"）可不改 |
| B2 | Minor | `firmware/twin/webapp/js/scene.js` L202 | 呼吸悬浮 `Math.sin(t/4)*0.3`（t 为秒）实际周期 8π≈25.1s；v2 设计 spec L33 与书稿均写"周期 4s"——实现未按设计落地 | 二选一：实现改 `Math.sin(t*Math.PI/2)*0.3`（周期 4s）；或改 spec+书稿为"周期≈25s" |
| B3 | Minor | `HANDOFF.md` L191 | 称费用 ≈360–720 元"（README-jlc-order.md **已改**）"，但 README-jlc-order.md §3 仍只有"按 5 片打样 550–1150"，无 360–720 更新——交接文档与事实不符 | README §3 补一行板 5 装 2 执行口径（≈360–720），或修正 HANDOFF 括注 |

---

## 5. 处置汇总（供修复代理执行）

**改书稿（8 项，均为 Minor）**
1. ch00a L73：六路并行 → 双路分时（+容量说明）。
2. ch02 tab:twin-apis：`GET/POST /api/time` → `POST /api/time`。
3. ch05 tab:fab-files：`assembly-top/bottom.pdf` → 两文件名并列（F3）。
4. ch06 L207：`flows/hotspots.json` → `flows.json` 与 `hotspots.json`（F4）；lst:mesh-verify 加省略标记。
5. ch07 L90/ch08 L101：`pn_core/cli.c`、`pn_core/ble_frame.c` → 补 `components/pn_core/src/` 前缀（F5/F6）；tab:fw-cli `G` 行 `<s>` → `<sensor>`。
6. ch08 L40："64 字节环形缓冲" → "64 字节行缓冲（最近一条应答）"。
7. ch09 L17：呼吸周期按 §4-B2 裁决改口径；bezier 句标注"设计令牌（spec）/实现 easeOutQuint"。
8. ch10 L48：encode 签名补 `: _t.Union[str, int]`（F13）。
9. ch11 L9/L217：api.sh 项数（50→43+11）、test_flows.py 路径、BRINGUP checkbox 数（30→36）。
10. ch00a/ch01：可选——"十二章"与印张 14 章的关系加半句说明；补 `\cite{ESP32S3DS}` 或删键（F7）。

**改检查器（3 项）**
- F1：valve_gpio 章模式 ch07→ch03；F2：explode_disp 章模式 ch13→ch11；snippet 检查容忍书稿声明省略（`...` 行）与字典行合并（F8/F9/F10/F12 误报消除）。

**修仓库（1 Critical + 2 Minor，用户裁决）**
- B1 qemu_smoke.sh 期望串 → `leak=off`（修后复跑留证）；B2 呼吸周期实现或口径二选一；B3 README-jlc-order 补 360–720 或改 HANDOFF 括注。

**重写章节（1 Critical）**
- ch12-product：按 HANDOFF 五项路线图 + Phase CAL/A301–A306 精度报告实质化（ch02/ch11 的前向引用全部悬空于此章）。

---

*审计完。机器检查器 13 条 findings 已全部复核（真 1 / 伪 12）；重点语义专项 9 项全部给出裁决；仓库侧问题 3 项单列待裁决。本报告仅报告，未修改任何书稿、代码或检查器。*
