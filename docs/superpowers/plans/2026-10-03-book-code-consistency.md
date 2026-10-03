# 一致性审查实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。

**Goal:** 按 spec `2026-10-03-book-code-consistency-design.md` 对 14 章书稿与仓库真源做机器+AI 双层一致性审查，修复全部漂移，产出审计报告。

**Tech Stack:** stdlib Python（机器检查器）· xelatex · 双代理分离（审计者≠修复者）

---

### Task 1: consistency_check.py 机器检查器（TDD）

**Files:** Create `book/tools/consistency_check.py`；Test `book/tools/test_consistency_check.py`

- [ ] **Step 1 失败测试**（KPY）：构造迷你书稿/真源 fixture 断言——常数提取核对（真源 3.269 书稿写 3.27→检出）、路径存在性（书稿引不存在文件→检出）、\cite 键差（书稿引 bib 无键→检出）、代码片段模糊匹配（去空白子串，书稿改一行语义→检出）
- [ ] **Step 2 实现**：
  - `CONSTANTS = {"vout":("3.269",["book/content/ch02*.tex","ch04?"]), "tau_ms":("1.79",...), "r_coil":("14",...), "crc_poly":("0x07",["book/content/ch08*.tex","ch10*.tex"]), "uuid_base":("f10a5c00",["ch08*.tex"]), "valve_gpio":("4,5,6,7,10,11,12,21"或逐个,["ch07*"]), "gamma":("1.2",["ch00b*"]), "orifice":("114.5",["ch00b*"]), "fee_low":("360",["ch05*"]), "fee_high":("720",["ch05*"]), "explode_disp":("10",["ch13*"])}`
  - 逐项：值在指定章文件出现（数字允许小数位差≤末位、允许中文单位邻接），不出现→finding
  - `check_paths(tex)`：书稿中 `\texttt{...}` 含 `/` 的 token → 仓库相对路径存在性（白名单：URL/非路径）
  - `check_cites(tex_files, bib)`：`\cite{a,b}` 键集合 vs bib `@xxx{key,` 键集合 → 双向差
  - `check_snippets(mapping)`：{tex 文件: (真源文件, 函数名)} 清单——从真源提取函数体（大括号计数）规范化（去空白/注释行）后断言书稿 lstlisting 含其首尾 5 行；mapping 覆盖 12 个代码列表（ch02 dP/dt 块、ch05 make_bom 段、ch06 尺寸链、ch07 tca_encode+pn_cmd_feed、ch08 state_pack、ch09 uGain、ch10 crc8+encode、ch11 ticket 用法、ch00b 孔口方程环境）
- [ ] **Step 3 红绿走完**；**Step 4 跑真书**：`KPY book/tools/consistency_check.py` → 输出 findings 清单（预期首批若干条，作为 Task 2 输入）
- [ ] **Step 5 提交** `feat(book): 一致性机器检查器 (常数/路径/cite/代码片段四类)`

### Task 2: AI 审计代理——14 章逐章 + 语义层

- [ ] **Step 1**: 派独立审计代理（不写代码只报告）：输入=spec §1 映射表+§2 七类清单+Task1 findings；方法=逐章读书稿 tex 与真源文件，重点语义漂移（如 GUI v1 残留描述、board_model 旧 τ 关断语义残留、sim 路径残留 hardware/…、命令表与 cli.c 实际不符、费用口径混乱 550-1150 vs 360-720 旧段残留）；机器项复核 findings 真伪
- [ ] **Step 2**: 产出 `book/AUDIT.md`：逐章表格（检查项/结论/证据/处置建议）+ 仓库侧真 bug 单列清单
- [ ] **Step 3 提交** `docs(book): 14 章一致性审计报告 AUDIT.md`

### Task 3: 修复代理——按 AUDIT.md 清零

- [ ] **Step 1**: 派修复代理执行 AUDIT.md 处置建议（只改书稿；仓库侧真 bug 若出现→不修，报告转用户）
- [ ] **Step 2**: 复跑 consistency_check.py 全绿 + xelatex 两遍零错 + 抽 3 处修复人工复核
- [ ] **Step 3 提交** `fix(book): 一致性修复 (AUDIT 全项清零)`

### Task 4: 终验 + 报告

- [ ] **Step 1**: 全测试矩阵抽查（test_webapp/classic×3/api×2 不回归）+ 一致性检查器输出全绿证据
- [ ] **Step 2**: HANDOFF.md 增"一致性审查"节（发现数/修复数/仓库侧遗留真 bug 清单）
- [ ] **Step 3 提交** `docs: 一致性审查闭环 + HANDOFF 更新`

## 完成定义
spec §5 四条：机器检查器全绿 / 14 章审计报告每章 ✅ / 仓库真 bug 清单呈用户 / xelatex 零错全提交。
