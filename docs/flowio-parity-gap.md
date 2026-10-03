# FlowIO 对标差距与 P2 集成路线（spec §1.3/§7 落地文档，plan T6）

> 日期: 2026-10-03 · 依据: FlowIO 论文（CHI'21 EA, Shtarbanov, aminer 被引 101）+ 本仓 P1 实况
> 用途: P2 候选集成清单（每项含空间/拓扑约束，供 device-geometry 框架"加数据+加断言"）

## 1. 差距总表（FlowIO 主模块 vs FLOWIO-CN P1）

| 能力 | FlowIO 主模块 | P1 现状 | 差距级 | P2 动作 |
|---|---|---|---|---|
| 阀 | 7× 常闭电磁阀**板载歧管**（2 进/出+5 通道） | 8 路外接阀驱动（MOSFET+端子） | ★★★ | **M2 阀板载化**（8 路一体） |
| 压力传感 | 1× 直连歧管（分时复用） | 无 | ★★★ | MPRLS 系 I2C，SURFACE 域近歧管 |
| 气路端口 | 5 气口（充/抽/泄/保持/测） | 无气路 | ★★★ | Ø2 快插口阵列（EDGE_OUT+pneumatic） |
| 电源 | 500mAh LiPo 藏阀下 + USB 充电 | DC005+USB-C 供电输入（或门） | ★★ | LiPo+充电 IC（低矮件入负 z 余量） |
| 传感 | 9-DoF IMU/气压计/光敏 | 无 | ★★ | IMU 模组（SURFACE，近主控） |
| 模块化 | 14-pin 磁吸 + 双硅胶管泵模块（S/M/L 37/90/251g） | TCA9548A 板内 I2C | ★ | 磁吸 4-pin+双气口 port 类型 |
| 软件 | BLE API/web-GUI/Arduino/JS | Web 孪生+浏览器仿真 ✓（已有亮点） | — | 保持优势，补 BLE API |

## 2. P2 候选件的空间/拓扑约束（框架直接消费）

- **阀排（M2-1 选型，JLC 真值入 devices.json）**：placement=EDGE_OUT；port.type=pneumatic；
  气口朝外侧同向阵列；与驱动 MOS（Q3-Q10 已有）加**域亲和边**（同列就近）；
  与歧管加 SPATIAL_SAME_DOMAIN 边；板上高 ≤14mm（壳预算）。
- **压力传感**：SURFACE 域；近歧管（亲和边）；I2C 地址与 TCA9548A 通道拓扑入网表。
- **LiPo+充电**：dims.h 精确入 z 栈（FlowIO 把电池藏阀下=板下负 z 空间利用，P1 壳
  底 2.4mm 壁+板底 7.4 铜柱区可容 ≤6mm 薄电芯）；充电 IC 近 USB-C（电气边短）。
- **IMU**：SURFACE；远离 L1 电感（min_distance 断言 ≥5mm，磁场干扰）。

## 3. 框架支撑模式（每项集成 = 加数据 + 加断言）
1. 选型 → jlcpcb MCP 摄取真值 → devices.json 加条目（dims/port/placement）；
2. 布局 → placement_advice（网表电气边 + 域亲和）出候选 → 人工/KiCad 定位；
3. 守门 → L5 自动断言：朝向/贴边/碰撞/槽匹配/钻孔避让/装配顺序；
4. 交付 → make_case/meshes/flows/assembly 全链重生成 + L1-L5 全绿。

## 4. 排期（spec §7 M2 里程碑）
M2-0 前置：本框架（T1-T7）交付 + P1 板到货 BRINGUP 通过（供电/8 路带载实测）
→ M2-1 选型（1 次会话）→ M2-2 布局约束 → M2-3 P2 全链交付（原理图增量+布局+
外壳+孪生+L1-L5）。启动时点：P1 到货验证后。

## 5. P1 带病放行清单（known-issues，P2 一并修）
| # | 问题 | 证据 | P2 动作 |
|---|---|---|---|
| 1 | C9(1206) 压 J9 XH 壳体 ~1.5×1.6mm | L5 FCL 装配态 | 移 C9 出壳体投影 |
| 2 | R3(100k) 藏 U1 WROOM 屏蔽罩下 | L5 FCL | 移出模块禁布 |
| 3 | J15/J16 壳体压 M3 孔(68,65)，螺丝头被卡 | L5 钻孔避让 | 孔位移或端子排让位 |
| 4 | 两 Ø0.3 过孔擦铜柱接触环 (82.7,12.9)/(4,40) | L5 钻孔避让 | 移孔 0.5mm |
| 5 | 端子高度两说（JLC 14.07 vs 模型 19.1 含 +3.5z 偏移） | make_assembly 噪声 | **板到货实测终裁** |
