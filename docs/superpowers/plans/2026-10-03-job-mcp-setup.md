# 求职 MCP 工具链安装实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。

**Goal:** 按 spec `2026-10-03-job-mcp-setup-design.md` 安装天眼查 MCP + mcp-jobs 并配置到 ZCode。

---

### Task 1: 天眼查 CLI 初始化 + 验证
- [ ] `tyc init --url "https://mcp.tianyancha.com/v1" --authorization "$(cat 简历/天眼查的key.txt)"`
- [ ] `tyc company registration-info "乐鑫信息科技（上海）股份有限公司" --head 20` 确认返回有效 JSON
- [ ] `tyc risk overview "乐鑫信息科技（上海）股份有限公司" --head 20` 确认风险模块可用

### Task 2: ZCode MCP 配置（两个 server 一次写入）
- [ ] 读 `~/.zcode/cli/config.json` 现有 mcp.servers
- [ ] 追加 tyc-mcp（SSE + Authorization header）和 mcp-jobs（stdio + npx）
- [ ] JSON 合法性验证

### Task 3: 安全确认 + 汇报
- [ ] `git ls-files 简历/` 确认 key 文件不在 git 索引
- [ ] `.gitignore` 确认 `/简历/` 已排除
- [ ] 汇报：两个 MCP 配置完成 + 下一步（重启会话后可用）

## 完成定义 = spec §5
