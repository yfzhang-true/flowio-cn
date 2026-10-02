# 理论篇实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。

**Goal:** 按 spec `2026-10-03-book-theory-part.md` 增设第 I 部理论两章 + reference.bib 引用体系，全书重号为三部结构。

**Tech Stack:** xelatex/MiKTeX · biblatex(或 bibtex 回退) · aminer/本地 literature 全文

---

### Task 1: reference.bib + 编译链打通
- 建 `book/reference.bib`：先落 12 条理论篇核心（Tao2019/Tao2022/Qi2021/Ren2024/Cai2023/Singh2024/Xavier2020AIM/Xavier2022Frontiers/Yao2013/Afsar2021/Shtarbanov2021/Xie2026/Yilmaz2026——条目从 aminer/literature 摘要与 DOI 手写）
- main.tex：`\usepackage[style=numeric,backend=biber]{biblatex}` + `\addbibresource` + `\printbibliography[heading=bibintoc]`；测 biber 可用性，缺则 `backend=bibtex` 回退（MiKTeX on-the-fly 装）
- 编译三遍零错、示例 \cite 渲染 [1] → 提交

### Task 2: 理论两章成文
- `content/ch00a-dt-theory.tex`、`ch00b-pneumatic-theory.tex` 按 spec §2 两表逐节写（3000-5000 字/章，≥6 \cite/章；Xavier 公式从 literature/2020-xavier-aim 全文转录 dP/dt 与孔口方程，FlowIO 章节引 shtarbanov 全文）
- 提交

### Task 3: 三部重号 + 实践章补引
- main.tex 排列：理论两章→原 ch01-ch10（\chapter 重号由 \part 分组自然顺延，无需改文件名，仅 main.tex 顺序+可选 \part{理论篇/实践篇/验收篇}）
- 原 ch01 生态位章头并入"1.5 本书路线图"交叉引用；各实践章各补 1-3 处 \cite（ch3←Tao 五维、ch7←TCA datasheet@misc、ch9←Liquid Glass HIG@misc）
- diff 确认实践内容零删改 → xelatex 零错 → 报页数 → 提交 `feat(book): 第I部理论篇成文+bib引用体系+三部重号 (70→~90页)`
