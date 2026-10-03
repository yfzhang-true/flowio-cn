# 全量公司尽调实施计划 v2（依据官方开发文档修订）

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。
> **v2 变更**: L0 锚定前置（USCC 精确查询）· 工具集按官方 162 清单校准（ipr-score/credit-evaluation/financial-summary/recruitment-info）· 全量 `--output-file` 留痕 · `sleep 2` 限流 · **删除 v1 的 `git add -f 简历/`（该目录按约束保持本地，不入 git）**

**Goal:** 按 spec v2 对 4 家匹配公司执行天眼查尽调，产出 `简历/公司尽调报告_上海嵌入式_2026-10.md`（本地）。

**工具:** tyc CLI v0.3.8（已验证）· 预算 ≤ 49 次有效调用（VIP 日额度 100）

**通用约定:**
- 目录：`mkdir -p 简历/tyc_data`，所有 JSON 落此
- 每条查询后 `sleep 2`（防 300004 限流）
- `<USCC_x>` 占位符 = Task 0 锚定提取的统一社会信用代码，下游查询一律用它作 searchKey
- `--head` 控制回显行数，`--output-file` 永远写全量
- 任何 300007/quota_exceeded → 立即停止，按 spec §5 降级顺序收尾

---

### Task 0: 实体锚定（4 次调用）

- [ ] `mkdir -p 简历/tyc_data`
- [ ] `tyc company companies "乐鑫" --head 30 --output-file 简历/tyc_data/anchor_espressif.json && sleep 2`
- [ ] `tyc company companies "恒玄" --head 30 --output-file 简历/tyc_data/anchor_bestechnic.json && sleep 2`
- [ ] `tyc company companies "紫光展锐" --head 30 --output-file 简历/tyc_data/anchor_unisoc.json && sleep 2`
- [ ] `tyc company companies "真兰仪表" --head 30 --output-file 简历/tyc_data/anchor_zhenglan.json && sleep 2`
- [ ] 逐一 Read anchor JSON：确认唯一主体（上海注册优先、登记状态=存续），提取 USCC → 记入本文件执行注记：
  - USCC_乐鑫 = `____`（期望主体：乐鑫信息科技（上海）股份有限公司）
  - USCC_恒玄 = `____`（期望主体：恒玄科技（上海）股份有限公司）
  - USCC_展锐 = `____`（待锚定确认全名）
  - USCC_真兰 = `____`（待锚定确认全名）
- [ ] 若某关键词返回多主体：选注册资本最大/状态存续/与 JD 所在地一致者，并在报告"基本画像"注明锚定依据

### Task 1: 乐鑫科技深度尽调（⭐ 第一优先，基础集 10 次）

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
- [ ] **条件项**：risk `_summary` 有司法案件 → `tyc risk judicial-case "<USCC_乐鑫>" --head 40 --output-file 简历/tyc_data/espressif_court.json`（重点：公司作为**被告/被上诉人**的案由）
- [ ] **条件项**：从 kp/sh 识别实控人（预期 张瑞安/TEO Swee Ann 线索）→ `tyc executive person-profile "<USCC_乐鑫>" --humanName "<姓名>" --head 60 --output-file 简历/tyc_data/espressif_person.json`
- [ ] 解析全部 JSON → 按 spec §3 模板写报告乐鑫章节

### Task 2: 恒玄科技尽调（基础集 10 次）

- [ ] 同 Task 1 命令集，USCC 换 `<USCC_恒玄>`，输出前缀 `bestechnic_`
- [ ] 条件项同 Task 1（judicial-case 视 `_summary`；person-profile 查实控人 张亮 线索，以 kp/sh 数据为准）

### Task 3: 紫光展锐 + 真兰仪表尽调（各 9 次，无 financial-summary）

- [ ] 展锐：Task 1 命令集去掉 financial-summary，USCC 换 `<USCC_展锐>`，前缀 `unisoc_`
- [ ] 真兰：同上，USCC 换 `<USCC_真兰>`，前缀 `zhenglan_`
- [ ] 展锐重点：股东结构（大基金/紫光集团线索）、司法与经营异常（集团层面风险传导）；真兰重点：匹配度首次评估（招聘信息可交叉验证 JD）

### Task 4: 报告生成 + 收尾

- [ ] 汇总全部 JSON → 生成 `简历/公司尽调报告_上海嵌入式_2026-10.md`（spec §3 模板 × 4 家）
- [ ] 报告头部附：查询时间、调用次数统计、数据来源目录说明
- [ ] 每公司给出 INFP 契合度评分 + 建议（✅ 投递 / ⏸ 观望 / ❌ 跳过）
- [ ] （可选）用 mcp-jobs `mcp_search_job` 交叉验证两家在招嵌入式岗位，写入"招聘活跃度"佐证
- [ ] **报告与 tyc_data 保持本地，不入 git**（简历/ 已 gitignore）
- [ ] 仅提交 spec/plan 的 v2 修订：`git add docs/superpowers/specs/2026-10-03-company-due-diligence-design.md docs/superpowers/plans/2026-10-03-company-due-diligence.md && git commit`
- [ ] 向用户汇报：报告路径 + 每家一句话结论 + 额度消耗

---

**执行注记（执行时填写）:**
- USCC 提取结果：见 Task 0
- 实际调用次数：__/49
- 异常与降级记录：无 / ____ 
