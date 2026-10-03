# 全量公司尽调 — 设计规格书 v3

> **日期**: 2026-10-03 · **状态**: 待用户审查
> **目标**: 对所有匹配岗位的目标公司做天眼查深度尽调，产出本地分析文档
> **依据**: 《简历/天眼查开发文档.txt》（官方全量文档）+ 用户指令（2026-10-03）

---

## 0. 修订历史

### v2 → v3（用户指令驱动）
| # | v2 做法 | v3 修正 | 依据 |
|---|---|---|---|
| 1 | 保守预算 ≤ 49 次（占日额度一半以内） | **额度用足策略**：目标发出 ~95 次调用，三波次架构（保底→深挖→机动），把 VIP 日额度转化为尽调深度 | 用户：「VIP 日额度要尽可能用完」 |
| 2 | 优先级仅体现在公司排序 | **优先级执行法则**（升级为硬约束）：任何低优先级公司的查询，不得先于高优先级公司的未完成波次执行；机动额度回注时也按优先级从高到低 | 用户：「按照匹配度优先级从高向低依次进行」 |
| 3 | 深度以 L1/L2 为主 | 深挖集/机动集放开 L3（上市公司专项、核心团队、财务指标、股权冻结等） | 额度允许 + 求职尽调价值 |

### v1 → v2（官方文档校准，摘要）
CLI 定案主通道（官方推荐）· L0 锚定拿 USCC 后全用 USCC · ipr-score 替代裸专利查询 · 新增 credit-evaluation / financial-summary / recruitment-info · 计费语义修正（仅成功且有数据扣次）· 删除 `git add -f 简历/`（该目录保持本地）· 公司数统一 4 家。

## 1. 尽调对象（4 家，执行顺序 = 本表自上而下）

| 执行序 | 公司 | L0 锚定词 | 已知主体全名（待 L0 确认） | 目标岗位 | 匹配度 |
|---|---|---|---|---|---|
| 1 ⭐ | 乐鑫科技 | `乐鑫` | 乐鑫信息科技（上海）股份有限公司（上市 688018） | 原型验证 / ESP-IDF SDK / AI 方案 | 85% / 75% / 80% |
| 2 | 恒玄科技 | `恒玄` | 恒玄科技（上海）股份有限公司（上市 688608） | IoT 嵌入式软件 | 65% |
| 3 | 紫光展锐 | `紫光展锐` | 待锚定（未上市） | 嵌入式软件工程师 | 55% |
| 4 | 真兰仪表 | `真兰仪表` | 待锚定（未上市） | 嵌入式软件（IoT/蓝牙） | 待评估 |

**优先级执行法则（硬约束）**：
1. 公司间顺序锁定为 乐鑫 → 恒玄 → 展锐 → 真兰，不并行、不跳跃；
2. 公司内顺序：保底集（W1）→ 深挖集（W2）→ 才允许进入下一家；
3. 机动集（W3）在 4 家 W1+W2 全部完成后启动，回注顺序仍从乐鑫开始；
4. 任何时刻额度被拦截（300007/quota_exceeded）：立即停止，已完成数据照常出报告，未完成项标注"额度耗尽待续"，次日 00:00 额度重置后可续跑（月额度 1000 次不构成约束）。

## 2. 查询协议（官方 L0→L1→L2→L3 + 三波次架构）

### 2.1 第 0 步：实体锚定（4 次）

```
tyc company companies "<锚定词>" --head 30 --output-file 简历/tyc_data/anchor_<key>.json
```
提取 USCC → 下游全部以 USCC 为 searchKey。多候选时选：上海注册 / 状态存续 / 注册资本最大者，并在报告注明锚定依据。

### 2.2 W1 保底集（每家必查，保证报告六维完整）

| 层 | CLI 命令 | 尽调问题 | 计次 |
|---|---|---|---|
| L1 | `tyc company registration-info` | 存续状态/注册资本/实缴/人数/经营范围 | 1 |
| L1 | `tyc risk overview` | 风险总览（`_summary` 分级） | 1 |
| L1 | `tyc history historical-overview` | 历史变更全维度——稳定性 | 1 |
| L1 | `tyc intellectual_property ipr-score` | 创新力评分（软著/专利/研发实力聚合） | 1 |
| L1 | `tyc operation credit-evaluation` | 税务评级 + 信用评级 | 1 |
| L2★ | `tyc company shareholder-info` | 股权结构/实控人线索 | 1 |
| L2 | `tyc company key-personnel` | 高管名单（person 下钻姓名来源） | 1 |
| L2 | `tyc operation recruitment-info` | 招聘活跃度（与 JD 交叉验证） | 1 |
| L2 | `tyc operation news-sentiment` | 舆情倾向 | 1 |
| L2 | `tyc company financial-summary` | 营收/净利/毛利率（**仅上市：乐鑫、恒玄**） | 1 或 0 |

W1 计次：乐鑫/恒玄 10，展锐/真兰 9。

### 2.3 W2 深挖集（按公司定制，额度用足的主战场）

**乐鑫（14 次，最深）**：judicial-case（诉讼画像，看被告身份与案由）· administrative-penalty · business-exception · actual-controller（实控人）· listing-info（上市信息/募资）· financial-main-indicators（L3，EPS/ROE/资产负债率，年+季）· stock-shareholders（L3，十大股东）· stock-violations（L3，违规处理——治理红旗）· team-members（L3，核心团队履历——INFP 文化判断关键输入）· annual-reports（L2，年报从业人数趋势=团队扩张史）· software-copyright-info（软著，固件公司相关）· patent-info（专利方向与岗位技术栈同频度）· executive person-profile + person-risk-overview（实控人画像+风险，`--humanName` 双参数锚定，预期线索张瑞安/TEO Swee Ann，以 kp 实际返回为准）

**恒玄（8 次）**：judicial-case · actual-controller · listing-info · financial-main-indicators · stock-violations · team-members · annual-reports · executive person-profile（实控人，预期线索张亮，以 kp 为准）

**展锐（7 次，侧重集团风险传导）**：judicial-case · administrative-penalty · business-exception · **equity-freeze（股权冻结——紫光系重点）** · actual-controller · annual-reports · team-members

**真兰（6 次，侧重成长性与匹配度初评）**：judicial-case · administrative-penalty · annual-reports · team-members · products-info · financing-records（未上市融资历史）

### 2.4 W3 机动集（W1+W2 全部完成后，按优先级回注至额度拦截止）

乐鑫：competitors（竞品格局）→ honor-info → change-records → products-info → income-statement → kp 中再选 1-2 名核心高管 person-profile → guarantee-info → 恒玄：stock-shareholders → software-copyright-info → patent-info → competitors → 展锐：financing-records → dishonest-info → 真兰：patent-info → software-copyright-info → ipr 补充项。

### 2.5 通用纪律

- 相邻调用 `sleep 2`（防 300004 限流）；失败重试 ≤ 2 次
- 空结果不扣费：非上市主体误触财务类工具无成本，但仍按 §2.2-2.4 清单规避无意义调用
- 每次 `--output-file 简历/tyc_data/<公司key>_<工具短名>.json`，`--head` 控回显

## 3. 分析框架（报告模板）

```
### 公司名（USCC，上市主体附股票代码）
#### 基本画像（状态/注册资本/实缴/人数/成立年份/上市信息）
#### 过去：关键变更时间线（名称/法人/注册资本/股东变更）
#### 现在：风险扫描（✅/⚠️/❌ 分级，逐项列依据：司法/行政处罚/经营异常/违规/担保）
#### 现在：技术实力（创新力评分拆解 + 专利/软著方向与岗位技术栈同频度）
#### 现在：经营健康（信用/税务评级 + 财务趋势[上市] + 招聘活跃度[与 mcp-jobs 交叉]）
#### 现在：团队与治理（实控人画像/核心团队履历/年报人数趋势/高管风险）
#### 将来：成长性评估（财务趋势 × 招聘信号 × 融资 × 舆情）
#### INFP 契合度评分（1-10：技术氛围/稳定性/成长性/规模适配/文化自治）
#### 建议（✅ 投递 / ⏸ 观望 / ❌ 跳过，附一句话理由）
```

## 4. 数据留痕

- 原始 JSON 全量落 `简历/tyc_data/`；报告结论逐项标注来源文件
- `简历/` 整体 gitignore（既定约束），原始数据与报告**均不入 git**
- v1 会话查询未落盘（已作废，重查）

## 5. 额度策略（用足但不透支）

- **权益**: VIP = 100 次/天（次日 00:00 重置）、1,000 次/月；仅成功且有数据扣次，报错/空结果免费；额度满后调用被拦截（不超额计费）
- **本任务发出量目标**: 锚定 4 + 乐鑫 24 + 恒玄 18 + 展锐 16 + 真兰 15 + 机动 ~18 ≈ **~95 次**（留 5 次余量吸收当日早前已消耗的少量验证调用）
- **实际计次预计 80-90**（部分风险类工具对健康企业返回空 = 免费）
- **台账**: plan 执行注记实时累计发出次数与拦截事件；报告头部公示最终统计
- **拦截止损**: 见 §1 优先级执行法则第 4 条

## 6. 渠道与工具状态（2026-10-03 复核）

| 渠道 | 状态 | 结论 |
|---|---|---|
| tyc CLI v0.3.8 | ✅ 已验证（162 工具 L0=1/L1=6/L2=57/L3=98） | **主通道**（官方「优先推荐使用CLI」） |
| tyc-mcp（ZCode 配置 sse + /v1） | ⚠️ 未挂载出工具 | 不阻塞；后续如需交互式查询改 `/mcp` + http 类型重配 |
| mcp-jobs | ✅ 已连通 | "招聘活跃度"章节交叉验证 |

## 7. 输出文件

- 报告：`简历/公司尽调报告_上海嵌入式_2026-10.md`（本地，不入 git）
- 原始数据：`简历/tyc_data/*.json`（本地，不入 git）
- 入 git 的仅 spec/plan 修订
