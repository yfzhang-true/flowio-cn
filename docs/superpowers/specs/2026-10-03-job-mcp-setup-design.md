# 求职 MCP 工具链安装 — 设计规格书

> **日期**: 2026-10-03 · **状态**: 待用户审查
> **目标**: 安装天眼查 MCP + mcp-jobs 职位聚合 MCP，配置到 ZCode，实现企业尽调与批量岗位查询

---

## 1. 天眼查 MCP（企业尽调）

### 现状
- `tyc-cli` **已安装**（v0.3.8，Node v24 就绪）
- API Key 在 `简历/天眼查的key.txt`：`mcpk2_p28HRXezQ7RjqQ-uKlIwNAXBAh5sFzxz`
- 用户有年费会员（VIP/SVIP 级权益）

### 安装步骤
1. **CLI 初始化**：`tyc init --url "https://mcp.tianyancha.com/v1" --authorization "<KEY>"`（用 API Key 兼容模式，因 ZCode 不支持 Remote MCP OAuth）
2. **MCP 配置**：在 `~/.zcode/cli/config.json` 的 `mcp.servers` 中添加：
```json
"tyc-mcp": {
  "type": "sse",
  "url": "https://mcp.tianyancha.com/v1",
  "headers": {"Authorization": "<KEY>"},
  "timeoutMs": 60000
}
```
3. **验证**：`tyc company registration-info "乐鑫信息科技（上海）股份有限公司" --head 20`
4. **重启会话**后 MCP 生效

### 使用场景（162 个工具 × 6 模块）
- **求职尽调**：查目标公司工商/风险/融资/舆情→判断公司健康度
- **面试准备**：查公司专利/软著→了解技术方向；查董监高→了解面试官背景

## 2. mcp-jobs 职位聚合 MCP

### 现状
- 源码在 `简历/mcp-jobs-main/`（用户已下载）
- **零配置**设计：`npx -y mcp-jobs` 即可启动
- 聚合多平台（猎聘/Boss/智联等）职位数据

### 安装步骤
1. **MCP 配置**：在 `~/.zcode/cli/config.json` 添加：
```json
"mcp-jobs": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "mcp-jobs"],
  "timeoutMs": 60000
}
```
2. **验证**：重启会话后调用搜索工具
3. 如果 npx 路径有问题，备选：全局安装 `npm install -g mcp-jobs` 后用绝对路径

## 3. 关于"猎聘/Boss/智联/国聘独立 MCP"的诚实回答

| 平台 | 官方 MCP | 现有替代 |
|---|---|---|
| 猎聘 | ❌ 无官方 API | ✅ liepin-cli skill（浏览器操作）+ mcp-jobs 聚合 |
| Boss直聘 | ❌ 无官方 API | ✅ bosszhipin skill（浏览器操作）+ mcp-jobs 聚合 |
| 智联招聘 | ❌ 无官方 API | ✅ mcp-jobs 聚合覆盖 |
| 国聘 | ❌ 无官方 API | ❌ 无替代（央企平台，需手动投递） |
| **天眼查** | ✅ **官方 MCP** | 162 个工具，年费会员权益 |

**根因**：招聘平台不开放公共 API（反爬 + 商业模式），因此没有独立的官方 MCP。**mcp-jobs 是目前最接近"批量查询"的开源方案**（内置爬虫聚合多平台），天眼查则是唯一有官方 MCP 的企业信息平台。

## 4. 安装后能力矩阵

| 能力 | 工具 | 使用方式 |
|---|---|---|
| 企业工商/风险/知产/舆情查询 | tyc-mcp（162 工具） | "查一下乐鑫科技的工商信息和风险概况" |
| 多平台职位批量搜索 | mcp-jobs | "搜索上海的ESP32嵌入式职位" |
| Boss直聘浏览器操作 | bosszhipin skill | 需浏览器环境 |
| 猎聘 CLI 操作 | liepin-cli skill | 需登录 |
| JD 解构/简历定制 | 3 个简历 skill | 已安装 |
| 公司深度分析（过去/现在/将来） | tyc-mcp history + operation + risk | "分析乐鑫科技的发展趋势" |

## 5. 完成定义
1. `tyc company registration-info "乐鑫..."` 返回有效 JSON
2. ZCode config.json 含 tyc-mcp + mcp-jobs 两个 server
3. 天眼查 key 不入 git（已确认简历/ 在 .gitignore）
4. 用户重启会话后两个 MCP 可用
