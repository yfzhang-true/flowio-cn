# GitHub 开源 + 简历重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。

**Goal:** 按 spec `2026-10-03-github-resume-design.md` 执行：GitHub 公开 repo 创建+推送 + 嵌入式工程师 Markdown 简历产出。

---

### Task 1: GitHub repo 创建 + 清洗 + push

- [ ] 用 PAT 调 GitHub API 创建 `flowio-cn` 公开 repo
- [ ] 本地 `.gitignore` 补排除：`简历/`、`宪法.md`、`操作手册.md`、`study-notes/`、`资源/工具链/`、`资源/实物图/`、`资源/器件规格书/`
- [ ] `git rm --cached` 对应已跟踪文件（磁盘保留）
- [ ] 写产品级 README.md（英文+中文双语、架构图引用、快速上手 3 步、License 三件套、GitHub Pages 链接预留）
- [ ] `git remote add origin https://<PAT>@github.com/<user>/flowio-cn.git && git push -u origin main`
- [ ] 验证：curl repo API 返回 200 + `git ls-remote origin` 有 main
- [ ] 提交 `feat: GitHub 开源——flowio-cn 全栈（固件+PCB+SDK+孪生+专著）`

### Task 2: 嵌入式简历 Markdown

- [ ] Write `简历/嵌入式软件工程师_张越飞.md`
  - 素材源：旧简历 PDF 提取文本 + 本 spec §2 对照表 + FLOWIO-CN 项目数据（DRC/测试/提交数）
  - FLOWIO-CN 项目节：架构图文字版 + 关键技术决策 5 条 + 数据（4 层 PCB/33 测试/BLE 四服务/94 页专著/GitHub 链接）
  - AG600 节：精简旧简历（保留 DO-178C/DSP/故障归零）
  - RFNext 节：进一步精简（一行定位+一句核心成果）
- [ ] 提交 `docs: 嵌入式工程师简历 Markdown`

### Task 3: 安全收尾

- [ ] `rm 简历/github的PAT.txt`（或移入系统密码管理器）
- [ ] `git log --all --diff-filter=A -- 简历/` 确认 PAT 从未入库
- [ ] HANDOFF.md 记录 GitHub repo URL
- [ ] 终提交

## 完成定义 = spec §4
