# 验收×专著一体化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 spec `2026-10-02-acceptance-book-design.md` 建立"验收工单→BRINGUP 勾选→书稿成章"三位一体机制：36 张工单模板 + ticket.py + 书稿 12 章骨架（3 章实文）+ BRINGUP 映射。

**Architecture:** 工单=双产物单元（YAML 元数据+Markdown 实录），ticket.py 管理（stdlib）；书稿 ElegantBook 已就绪（MiKTeX xelatex）；素材管线=figures/data 目录约定 + \includegraphics 引用。

**Tech Stack:** Python stdlib（ticket.py）· xelatex/MiKTeX · Git
**约定:** 命令自 `E:/FLOWIO/`；KPY=`"E:/Program Files/KiCad/10.0/bin/python.exe"`；文件写用 Path.write_bytes；每 Task 末提交。

---

### Task 1: ticket.py 工单管理器（TDD）

**Files:** Create `book/tools/ticket.py`；Test `book/tools/test_ticket.py`

- [ ] **Step 1 失败测试**（KPY 跑）：
```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ticket
def test_new_and_report(tmp="book/tickets"):
    t = ticket.new("A205", "WS2812 状态灯", phase="hw", bringup="5.1", book_ch=11, root=".")
    assert t["status"] == "pending" and os.path.isfile("book/tickets/A205.yaml")
    rep = ticket.report(root=".")
    assert any(l.startswith("A205") and "pending" in l for l in rep.splitlines())
if __name__ == "__main__":
    import shutil; shutil.rmtree("book/tickets", ignore_errors=True)
    test_new_and_report(); shutil.rmtree("book/tickets", ignore_errors=True)
    print("ticket tests OK")
```
- [ ] **Step 2 确认失败** → **Step 3 实现**（stdlib：yaml 手解析/生成用行格式避免外部 yaml 依赖——`key: value` 行 + 正文 `---` 分隔；new 写模板含 evidence_required 等全字段与正文骨架；report 扫 tickets/*.yaml 汇总 `{id,title,phase,status}` 表格文本；另 `set_status(id, s, root)` 子命令）→ **Step 4 跑通** → **Step 5 提交** `feat(book): ticket.py 工单管理器 (new/report/set_status, stdlib-yaml)`

### Task 2: 36 张工单批量生成

**Files:** Create `book/tools/gen_tickets.py` + `book/tickets/A*.yaml` ×36

- [ ] **Step 1** gen_tickets.py 内含 36 行清单（id/title/phase/bringup/book_ch——照 spec §2 三表全文），逐张调 ticket.new 落盘（SW 六张 status=pass 并在正文写入证据链接：`firmware/twin/shots/v2_*.png`、`test_webapp.js 44 断言`、`sdk/python/tests 9 向量`、`firmware/tests 33 绿`、`BLE.md §4.1/4.2 向量`）
- [ ] **Step 2** 跑 `KPY book/tools/gen_tickets.py` → `KPY book/tools/ticket.py report`（root=book 或适配）打印 36 行表（pass 6/pending 30）
- [ ] **Step 3 提交** `feat(book): 36 张验收工单 (SW6 预填 pass+证据, HW24+CAL6 模板)`

### Task 3: 书稿 12 章骨架 + 3 章实文

**Files:** `book/content/ch01..ch12.tex`（新建）；改 `book/main.tex`（\input 全章）；改 `book/figures/`（补实文所需图）

- [ ] **Step 1** 12 个 .tex：每章 `\chapter{标题}\label{ch:n}` + 3-5 个 `\section`（标题按 spec §3 表内容提纲）。**实文三章**：
  - ch3 原理图：从 `docs/superpowers/specs/2026-10-01-flowio-p1-pcb-design.md` 修正日志（#9 SS34 或门/#11 反馈电阻/#12 CH340K）写"三个真实修正案例"小节（每例：症状→根因→修法，引用 gen_sch.py 代码行）
  - ch4 PCB：从 git log d549f4a/cd47167/a38172a 提取"146→17→6→0"四阶段叙事（含天线禁布区丢失目视检查故事）+ r_top.png/r_bot.png 为图
  - ch11 扩写：在现有基础上加 36 工单总表（tabular）+ SW 六项 pass 记录节
- [ ] **Step 2** main.tex \input ch01-ch12 + \appendix 移后；拷 `hardware/flowio-p1/r_top.png`、`r_bot.png` 至 figures/
- [ ] **Step 3** xelatex 两遍零错；页数 >12 → **Step 4 提交** `feat(book): 12 章骨架 + ch3/4/11 实文 (修正案例/布线攻坚/验收总表)`

### Task 4: BRINGUP 映射 + 终验提交

- [ ] **Step 1** `firmware/BRINGUP.md` 每章标题行后加 `> 对应工单: A2xx`（九章九行，Edit 工具）
- [ ] **Step 2** 终验：ticket report（6 pass/30 pending）+ xelatex 零错 + test_ticket.py OK + 四套现有测试不回归（test_webapp/classic×3）
- [ ] **Step 3** `git add -A book firmware/BRINGUP.md && git commit -m "feat: 验收×专著一体化——36工单/12章骨架/3章实文/BRINGUP映射"` → 更新 HANDOFF.md 一行（工单机制说明+下一步=回板执行 A2xx）

## 完成定义
spec §6 四条门槛逐条可指认；书稿编译零错且含实文；验收工作随时可从任意一张 A2xx 工单开始。
