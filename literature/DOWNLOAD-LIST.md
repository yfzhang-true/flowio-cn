# 待下载文献清单（自动化受阻，请用户手动获取）

> 下载后放入本目录（E:\FLOWIO\literature\），AI 将继续提取阅读并纳入 SPEC。
> 受阻原因均为反爬机制，与网络无关。

## ① 强烈推荐（物理 SPEC 标定关键）

**Shtarbanov MIT 硕士学位论文**（FlowIO 完整设计/制作指南，含各泵模块实测压力-流量数据——Table 1 的扩展版）
- 直链：https://dspace.mit.edu/bitstreams/e2f98dce-97ec-4c01-b53d-8954074cc039/download
- 受阻：**AWS WAF 人机验证**（CAPTCHA，curl 无法通过；浏览器打开即触发验证，人工点击后可下载）
- 备选入口：在 dspace.mit.edu 搜索 "Shtarbanov FlowIO"

## ② 可选（界面/应用参考）

| 文献 | 入口 | 受阻原因 |
|------|------|---------|
| **PneuBots**: Modular Inflatables for Playful Exploration of Soft Robotics（Shtarbanov, TEI'22） | ACM DL 搜 "PneuBots"，或 dspace.mit.edu（同样有 WAF） | ACM Cloudflare 拦 curl；dspace WAF |
| **OmniFiber**: Integrated Fluidic Fiber Actuators（UIST'21） | ACM DOI 10.1145/3472749.3474805 或 tangible.media.mit.edu | ACM 拦截 |
| **MorphIO**: Entirely Soft Sensing and Actuation Modules（FlowIO 引文，实体交互编程） | ACM DL 搜 "MorphIO" | ACM 拦截 |

## ③ 可选（物理建模进阶，付费墙）

| 文献 | 入口 | 说明 |
|------|------|------|
| Lumped-Parameter Response Time Models for Pneumatic Circuits（ASME 2020） | asmedigitalcollection.asme.org | 管路流阻/响应时间模型；机构订阅可下 |
| Xavier 等 Modelling and Simulation of Pneumatic Sources for Soft Robots（IEEE） | precisionmechatronicslab.com 出版物页 | 泵源集总参数建模（2022 Frontiers 已覆盖核心方程，优先级低） |

---
已入手三篇见 [README.md](README.md)。本清单文件会随获取进展更新。
