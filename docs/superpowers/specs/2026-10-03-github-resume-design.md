# GitHub 开源上传 + 嵌入式简历重构 — 设计规格书

> **日期**: 2026-10-03 · **状态**: 待用户审查
> **前置**: FLOWIO-CN 全栈交付（DRC 0/0 · 测试 200+ 全绿 · 书稿 94 页）；用户已有产品经理简历

---

## 1. GitHub 开源上传（要求 1）

### 1.1 仓库结构（公开 repo `flowio-cn`）

```
github.com/yfzhang-true/flowio-cn/
├── README.md              ← 产品级 README（英文+中文，含架构图/视频链接/快速上手）
├── LICENSE                ← 三件套：代码 MIT / 硬件 CERN-OHL-S / 文档 CC BY-NC-ND
├── firmware/              ← 全部（含 twin/deprecated 归档标注）
├── hardware/flowio-p1/    ← KiCad 工程 + fab 包（不含 资源/ 大文件）
├── sdk/python/            ← flowio_sdk
├── book/                  ← LaTeX 专著源码（含 content/figures/reference.bib）
├── docs/superpowers/      ← 全部 spec+plan（过程文档价值：展示工程方法论）
├── 资源/README.md         ← 仅清单（引用方需自行获取规格书 PDF）
└── .gitignore             ← 已有
```

### 1.2 上传前清洗（关键）

| 排除 | 理由 |
|---|---|
| `简历/` 目录（含 PAT.txt！） | **安全**——PAT 绝不入库 |
| `资源/` 实物图+规格书 PDF | 版权（厂商规格书不公开分发） |
| `资源/工具链/` 1.6G | 工具链非产品 |
| `literature/*.pdf` | 论文版权（txt 已入 gitignore） |
| `flowio-softrobotics-docs/` | MIT FlowIO 官方文档（可公开，保留） |
| `firmware/build/` `.mimosa/` `.git/` | 构建产物/扫描/版本控制 |
| `宪法.md` `操作手册.md` | 个人文档 |
| `study-notes/` | 个人笔记（可选择性纳入，待用户裁定） |

### 1.3 执行方式

```bash
# 1. 创建远端 repo（用 PAT）
curl -H "Authorization: token <PAT>" https://api.github.com/user/repos \
  -d '{"name":"flowio-cn","description":"...","public":true}'

# 2. 用 git filter-repo 或直接新建 worktree + git push
# 推荐：直接在当前 repo 加 remote + push（git 历史保留完整）
```

## 2. 嵌入式简历重构（要求 2）

### 2.1 目标岗位匹配分析

从 JD 中提取的嵌入式核心要求 vs FLOWIO-CN 交付的对应能力：

| JD 要求（乐鑫嵌入式岗） | FLOWIO-CN 实证 |
|---|---|
| 精通 C 语言 + FreeRTOS | pn_core 纯逻辑层 C 开发 + ESP-IDF FreeRTOS 10ms 任务 |
| 熟悉 I2C/SPI/UART 等外设 | TCA9548A I2C 复用驱动 + WS2812 RMT + UART CLI + BLE GATT |
| 具备嵌入式系统编程能力 | ESP32-S3 全栈：4 层 PCB→SMT→固件→BLE→孪生→SDK |
| Python 脚本/工具开发 | 整孪生平台 Python（server/sim/board_model/SDK）|
| 熟悉电子实验室仪表 | BRINGUP 回板动线（示波器/逻辑分析仪/万用表） |
| 具备优秀调试技术 | DRC 146→0 四阶段攻坚 + 16 项一致性审查 |
| AI 技术引入研发实践 | **AI Agent 驱动开发全流程**（本项目即证明）|
| 版本控制 Git/GitHub | git 200+ commits + spec/plan/test 全流程 |

### 2.2 简历定位转向

| 维度 | 旧（产品经理） | 新（嵌入式工程师） |
|---|---|---|
| 核心定位 | "技术翻译者" | **"全栈嵌入式工程师——从 PCB 到云端孪生"** |
| 关键词 | 需求/产品/MVP | ESP32/FreeRTOS/BLE/KiCad/数字孪生/自动化测试 |
| 项目排序 | RFNext→AI助手→AG600 | **FLOWIO-CN（最新+最重）**→AG600（嵌入式本源）→RFNext（工具能力） |
| GitHub | 无 | **github.com/yfzhang-true/flowio-cn（硬件+固件+SDK+专著 94 页全开源）** |

### 2.3 履历时间线

```
2026.07 - 至今    空窗期 → FLOWIO-CN 气动软体机器人控制平台（独立研发）
2025.12 - 2026.07  睿创微纳 AI 研发工程师（射频 EDA 自动化）
2023.07 - 2025.06  中航上海航空电器 嵌入式软件开发工程师（AG600 SSPC）
2020.09 - 2023.06  北京工业大学 电子信息硕士（人工智能/机械臂）
2015.09 - 2019.06  江苏理工学院 自动化本科
```

### 2.4 简历文件

`简历/嵌入式软件工程师_张越飞.md`（Markdown，~2 页当量，中文）

结构：
```
# 张越飞 — 嵌入式软件工程师
联系方式 | GitHub: github.com/yfzhang-true/flowio-cn
## 核心定位（3 行）
## 技术栈（表格）
## 项目经历
### FLOWIO-CN（2026.07-至今，独立研发）——重点 60%
### AG600 SSPC（2023-2025）——嵌入式本源 25%
### RFNext 射频自动化（2025-2026）——工具能力 15%
## 工作经历
## 教育经历
```

## 2.5 已安装简历编制 Skills（cocoloop → skills.sh → GitHub）

| Skill | 来源 | 用途 |
|---|---|---|
| `tech-resume-optimizer` | paramchoudhary/resumeskills (9434 安装) | 技术简历结构/ATS/关键词优化 |
| `resume-tailor` | 同上 (9487 安装) | 按 JD 定制——重排经历/调整摘要/补关键词 |
| `job-description-analyzer` | 同上 (8969 安装) | 解构 JD 提取核心要求与优先级 |

安装位置：`~/.agents/skills/`（ZCode 兼容目录）。执行 Task 2 时**先调 job-description-analyzer 解构乐鑫 JD → 再调 resume-tailor 定位 → 最后 tech-resume-optimizer 结构化输出**。

## 3. 执行边界

- PAT 保留在本地 `简历/github的PAT.txt`（用户裁定），但**必须**确保不被 git 跟踪和上传——加入 .gitignore + git ls-remote 确认
- 简历不含虚构成分——所有技术声明可指认 repo 提交
- 专著同步上传（用户裁定"项目和专著都开源"）

## 4. 完成定义
1. GitHub repo 公开可访问，README 渲染正常，LICENSE 三件套就位
2. 简历 Markdown 产出且用户确认
3. PAT 不留任何持久化文件
