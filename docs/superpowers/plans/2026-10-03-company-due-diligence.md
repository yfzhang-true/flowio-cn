# 全量公司尽调实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。

**Goal:** 按 spec 对 4 家匹配公司执行天眼查 6 模块尽调，产出 `简历/公司尽调报告_上海嵌入式_2026-10.md`。

**工具:** tyc CLI（已验证连通）· 6 模块 × 4 公司

---

### Task 1: 乐鑫科技深度尽调（⭐ 第一优先）
- [ ] `tyc company registration-info "乐鑫信息科技（上海）股份有限公司" --output-file 简历/tyc_espressif_reg.json`
- [ ] `tyc risk overview "乐鑫信息科技（上海）股份有限公司" --output-file 简历/tyc_espressif_risk.json`
- [ ] `tyc company shareholder-info "乐鑫信息科技（上海）股份有限公司" --output-file 简历/tyc_espressif_sh.json`
- [ ] `tyc intellectual_property patent-info "乐鑫信息科技（上海）股份有限公司" --head 20 --output-file 简历/tyc_espressif_patent.json`
- [ ] `tyc operation news-sentiment "乐鑫信息科技（上海）股份有限公司" --head 20 --output-file 简历/tyc_espressif_news.json`
- [ ] `tyc history historical-overview "乐鑫信息科技（上海）股份有限公司" --head 20 --output-file 简历/tyc_espressif_hist.json`
- [ ] 解析 JSON → 按 spec §3 模板写入报告

### Task 2: 恒玄科技尽调
- [ ] 同上 6 项，主体名："恒玄科技（上海）股份有限公司"

### Task 3: 紫光展锐 + 真兰仪表尽调
- [ ] 同上 6 项 × 2 家
- [ ] 主体名：先用 `tyc company companies` 锚定准确全名

### Task 4: 报告生成 + INFP 评估 + 提交
- [ ] 解析全部 JSON → 按模板生成 `简历/公司尽调报告_上海嵌入式_2026-10.md`
- [ ] 每公司含 INFP 契合度 + 建议（投递/观望/跳过）
- [ ] 清理中间 JSON（或归档到子目录）
- [ ] `git add -f 简历/公司尽调报告*.md && git commit`
