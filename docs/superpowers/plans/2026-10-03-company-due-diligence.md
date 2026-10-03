# 全量公司尽调实施计划 v3

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。
> **v3 变更**（用户指令：额度用足 + 匹配度优先级从高向低）：
> ① 三波次架构 W1 保底 / W2 深挖 / W3 机动，目标发出 ~95 次调用；
> ② 优先级执行法则升级为硬约束：乐鑫 → 恒玄 → 展锐 → 真兰，公司内 W1→W2 完成后才进下一家，W3 最后按优先级回注；
> ③ 深挖集放开 L3 工具（上市公司专项/核心团队/财务指标/股权冻结）。

**Goal:** 按 spec v3 对 4 家匹配公司执行天眼查尽调，产出 `简历/公司尽调报告_上海嵌入式_2026-10.md`（本地）。

**工具:** tyc CLI v0.3.8（已验证）· 目标发出 ~95 次（VIP 日额度 100）

**通用约定:**
- `mkdir -p 简历/tyc_data`；每条查询 `--output-file 简历/tyc_data/<前缀>_<工具>.json` + `sleep 2`
- `<USCC_x>` = Task 0 锚定提取的统一社会信用代码，下游一律用它
- 300007/quota_exceeded → 立即停止出报告，未完成项标"额度耗尽待续"（次日可续）
- 台账：执行注记实时累计发出次数

---

### Task 0: 实体锚定（4 次）

- [ ] `mkdir -p 简历/tyc_data`
- [ ] `tyc company companies "乐鑫" --head 30 --output-file 简历/tyc_data/anchor_espressif.json && sleep 2`
- [ ] `tyc company companies "恒玄" --head 30 --output-file 简历/tyc_data/anchor_bestechnic.json && sleep 2`
- [ ] `tyc company companies "紫光展锐" --head 30 --output-file 简历/tyc_data/anchor_unisoc.json && sleep 2`
- [ ] `tyc company companies "真兰仪表" --head 30 --output-file 简历/tyc_data/anchor_zhenglan.json && sleep 2`
- [ ] 逐一 Read anchor JSON 确认唯一主体（上海/存续优先），提取 USCC 记入执行注记：
  - USCC_乐鑫 = `____`（期望：乐鑫信息科技（上海）股份有限公司）
  - USCC_恒玄 = `____`（期望：恒玄科技（上海）股份有限公司）
  - USCC_展锐 = `____`（全名待确认）
  - USCC_真兰 = `____`（全名待确认）

### Task 1: 乐鑫科技（⭐ 执行序 1，W1 10 次 + W2 14 次 = 24 次）

**W1 保底集：**
- [ ] `tyc company registration-info "<USCC_乐鑫>" --head 80 --output-file 简历/tyc_data/espressif_reg.json && sleep 2`
- [ ] `tyc risk overview "<USCC_乐鑫>" --head 80 --output-file 简历/tyc_data/espressif_risk.json && sleep 2`
- [ ] `tyc history historical-overview "<USCC_乐鑫>" --head 60 --output-file 简历/tyc_data/espressif_hist.json && sleep 2`
- [ ] `tyc intellectual_property ipr-score "<USCC_乐鑫>" --head 40 --output-file 简历/tyc_data/espressif_ipr.json && sleep 2`
- [ ] `tyc operation credit-evaluation "<USCC_乐鑫>" --head 40 --output-file 简历/tyc_data/espressif_credit.json && sleep 2`
- [ ] `tyc company shareholder-info "<USCC_乐鑫>" --head 60 --output-file 简历/tyc_data/espressif_sh.json && sleep 2`
- [ ] `tyc company key-personnel "<USCC_乐鑫>" --head 40 --output-file 简历/tyc_data/espressif_kp.json && sleep 2`
- [ ] `tyc operation recruitment-info "<USCC_乐鑫>" --head 40 --output-file 简历/tyc_data/espressif_recruit.json && sleep 2`
- [ ] `tyc operation news-sentiment "<USCC_乐鑫>" --head 30 --output-file 简历/tyc_data/espressif_news.json && sleep 2`
- [ ] `tyc company financial-summary "<USCC_乐鑫>" --head 40 --output-file 简历/tyc_data/espressif_fin.json && sleep 2`

**W2 深挖集：**
- [ ] `tyc risk judicial-case "<USCC_乐鑫>" --head 40 --output-file 简历/tyc_data/espressif_court.json && sleep 2`（重点：被告/被上诉人身份与案由）
- [ ] `tyc risk administrative-penalty "<USCC_乐鑫>" --head 30 --output-file 简历/tyc_data/espressif_penalty.json && sleep 2`
- [ ] `tyc risk business-exception "<USCC_乐鑫>" --head 20 --output-file 简历/tyc_data/espressif_bizex.json && sleep 2`
- [ ] `tyc company actual-controller "<USCC_乐鑫>" --head 30 --output-file 简历/tyc_data/espressif_ctrl.json && sleep 2`
- [ ] `tyc company listing-info "<USCC_乐鑫>" --head 40 --output-file 简历/tyc_data/espressif_listing.json && sleep 2`
- [ ] `tyc company financial-main-indicators "<USCC_乐鑫>" --head 40 --output-file 简历/tyc_data/espressif_findicator.json && sleep 2`（EPS/ROE/资产负债率，年+季）
- [ ] `tyc company stock-shareholders "<USCC_乐鑫>" --head 40 --output-file 简历/tyc_data/espressif_top10.json && sleep 2`（十大股东）
- [ ] `tyc company stock-violations "<USCC_乐鑫>" --head 30 --output-file 简历/tyc_data/espressif_violation.json && sleep 2`（违规处理——治理红旗）
- [ ] `tyc operation team-members "<USCC_乐鑫>" --head 40 --output-file 简历/tyc_data/espressif_team.json && sleep 2`（核心团队履历——INFP 文化判断）
- [ ] `tyc company annual-reports "<USCC_乐鑫>" --head 30 --output-file 简历/tyc_data/espressif_annual.json && sleep 2`（从业人数趋势）
- [ ] `tyc intellectual_property software-copyright-info "<USCC_乐鑫>" --head 30 --output-file 简历/tyc_data/espressif_swcopy.json && sleep 2`
- [ ] `tyc intellectual_property patent-info "<USCC_乐鑫>" --head 30 --output-file 简历/tyc_data/espressif_patent.json && sleep 2`
- [ ] 从 kp/ctrl/sh 确认实控人姓名（预期张瑞安/TEO Swee Ann 线索，以数据为准）→ `tyc executive person-profile "<USCC_乐鑫>" --humanName "<姓名>" --head 60 --output-file 简历/tyc_data/espressif_person1.json && sleep 2`
- [ ] `tyc executive person-risk-overview "<USCC_乐鑫>" --humanName "<同上姓名>" --head 40 --output-file 简历/tyc_data/espressif_person1risk.json && sleep 2`
- [ ] 解析全部 JSON → 写报告乐鑫章节（spec §3 模板）

### Task 2: 恒玄科技（执行序 2，W1 10 次 + W2 8 次 = 18 次）

**W1 保底集：** 同 Task 1 W1 十条命令，USCC 换 `<USCC_恒玄>`，输出前缀 `bestechnic_`。

**W2 深挖集：**
- [ ] `tyc risk judicial-case` → `bestechnic_court.json`
- [ ] `tyc company actual-controller` → `bestechnic_ctrl.json`
- [ ] `tyc company listing-info` → `bestechnic_listing.json`
- [ ] `tyc company financial-main-indicators` → `bestechnic_findicator.json`
- [ ] `tyc company stock-violations` → `bestechnic_violation.json`
- [ ] `tyc operation team-members` → `bestechnic_team.json`
- [ ] `tyc company annual-reports` → `bestechnic_annual.json`
- [ ] 实控人（预期张亮线索，以 kp 为准）`tyc executive person-profile --humanName` → `bestechnic_person1.json`
- [ ] 解析 → 写报告恒玄章节

### Task 3: 紫光展锐 + 真兰仪表（执行序 3、4）

**展锐（W1 9 次 + W2 7 次 = 16 次，无 financial-summary）：**
- [ ] W1：Task 1 W1 去掉 financial-summary，USCC `<USCC_展锐>`，前缀 `unisoc_`
- [ ] W2：`tyc risk judicial-case` → `unisoc_court.json` · `tyc risk administrative-penalty` → `unisoc_penalty.json` · `tyc risk business-exception` → `unisoc_bizex.json` · **`tyc risk equity-freeze` → `unisoc_freeze.json`（股权冻结——紫光系重点）** · `tyc company actual-controller` → `unisoc_ctrl.json` · `tyc company annual-reports` → `unisoc_annual.json` · `tyc operation team-members` → `unisoc_team.json`
- [ ] 解析 → 写报告展锐章节（重点：集团风险传导评估）

**真兰（W1 9 次 + W2 6 次 = 15 次）：**
- [ ] W1：同展锐（无 financial-summary），USCC `<USCC_真兰>`，前缀 `zhenglan_`
- [ ] W2：`tyc risk judicial-case` → `zhenglan_court.json` · `tyc risk administrative-penalty` → `zhenglan_penalty.json` · `tyc company annual-reports` → `zhenglan_annual.json` · `tyc operation team-members` → `zhenglan_team.json` · `tyc operation products-info` → `zhenglan_products.json` · `tyc operation financing-records` → `zhenglan_financing.json`
- [ ] 解析 → 写报告真兰章节（重点：匹配度首次评估，招聘信息交叉 JD）

### Task 4: W3 机动集（4 家 W1+W2 完成后，按优先级回注至额度拦截止，~18 次）

按序执行，每条后查额度是否被拦截（300007），拦截即止：
- [ ] 乐鑫：`tyc operation competitors` → `espressif_competitors.json`
- [ ] 乐鑫：`tyc operation honor-info` → `espressif_honor.json`
- [ ] 乐鑫：`tyc company change-records` → `espressif_changes.json`
- [ ] 乐鑫：`tyc operation products-info` → `espressif_products.json`
- [ ] 乐鑫：`tyc company income-statement` → `espressif_income.json`
- [ ] 乐鑫：kp 中再选 1-2 名核心高管（CTO/联创优先）`tyc executive person-profile --humanName` → `espressif_person2.json`（可多条）
- [ ] 乐鑫：`tyc risk guarantee-info` → `espressif_guarantee.json`
- [ ] 恒玄：`tyc company stock-shareholders` → `bestechnic_top10.json`
- [ ] 恒玄：`tyc intellectual_property software-copyright-info` → `bestechnic_swcopy.json`
- [ ] 恒玄：`tyc intellectual_property patent-info` → `bestechnic_patent.json`
- [ ] 恒玄：`tyc operation competitors` → `bestechnic_competitors.json`
- [ ] 展锐：`tyc operation financing-records` → `unisoc_financing.json`
- [ ] 展锐：`tyc risk dishonest-info` → `unisoc_dishonest.json`
- [ ] 真兰：`tyc intellectual_property patent-info` → `zhenglan_patent.json`
- [ ] 真兰：`tyc intellectual_property software-copyright-info` → `zhenglan_swcopy.json`

### Task 5: 报告生成 + 收尾

- [ ] 汇总全部 JSON → `简历/公司尽调报告_上海嵌入式_2026-10.md`（spec §3 模板 × 4 家）
- [ ] 报告头部：查询时间 / 发出调用数 / 预计计次数 / 数据来源目录
- [ ] 每公司 INFP 契合度评分 + 建议（✅ 投递 / ⏸ 观望 / ❌ 跳过）
- [ ] （可选）mcp-jobs `mcp_search_job` 交叉验证在招嵌入式岗位写入"招聘活跃度"
- [ ] 报告与 tyc_data **保持本地不入 git**；仅提交 spec/plan v3：
      `git add docs/superpowers/specs/2026-10-03-company-due-diligence-design.md docs/superpowers/plans/2026-10-03-company-due-diligence.md && git commit`
- [ ] 向用户汇报：报告路径 + 每家一句话结论 + 额度消耗台账

---

**执行注记（2026-10-03 执行完毕回填）:**
- USCC：乐鑫 `913101156745626329` · 恒玄 `91310115341975375J` · 展锐 `91110000076595389X`（全名：紫光展锐（上海）科技股份有限公司）· 真兰 `91310000586778185R`（上海真兰仪表科技股份有限公司，创业板 301303——v2 按"未上市"处理有误，执行中纠正并补财务查询；安徽同名主体为其 100% 子公司）
- 发出调用数：Task0 4 / Task1 乐鑫 24 / Task2 恒玄 17 / Task3 展锐 15 + 真兰 17 / Task4 W3 19 / **合计 96 / 95 目标**
- SVIP 拦截（403 不计费，6 次）：actual-controller（乐鑫）、person-profile、person-risk-overview（乐鑫）、equity-freeze（展锐）、competitors、guarantee-info（乐鑫 W3）——后续恒玄/展锐/真兰的同类调用直接取消，用 listing-info 实控人字段 + team-members 履历替代
- 空结果（不计费，~9 次）：处罚/经营异常/失信类为空 = 无此类风险；展锐 ipr-score 空（专利在子公司）
- 网络失败重试：2 次（fetch failed，均重试成功）
- **预计实际计次 ~81 / 100 日额度**
- 产出：`简历/公司尽调报告_上海嵌入式_2026-10.md`（四家全量章节 + 横向对比 + 行动清单）+ `简历/tyc_data/` 89 个原始 JSON
- 结论排序：乐鑫 ✅ 投递（9/10）> 恒玄 ⏸ 可投 BLE 岗（6.5/10）> 真兰 ⏸ 保底（5.5/10）> 展锐 ❌ 跳过（4.5/10）
