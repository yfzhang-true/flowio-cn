# 资源纳编 + 空间释放实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。

**Goal:** 按 spec `2026-10-03-assets-triage-design.md` 将 资源/ 实物级信息源编入书稿（bib+6 章增补+图规范化），并按用户批准档位执行 外部参考/ 清理。

**Tech Stack:** xelatex/biber · 资源图拷贝规范化 · du/rm 谨慎执行

---

### Task 1: bib 增补 + 器件图规范化入 figures/
- [ ] reference.bib 增 10 条 @misc（0520D/0520F 规格书、XGZP V1.1+V2.5、AO3400A、CDRH103RNP、DC005、XH2.54、CH340N、DevKitC-1 SCH、FlowIO Arduino 库、官方 3MF 集——题名/厂商/年份从 PDF 元数据或文件名转录，不编造版本号）
- [ ] 拷图并重命名入 book/figures/：fig-valve-0520d-top.png（valve0520d_p1_top）、fig-valve-0520f-3way.png（valve0520f_p1_mid）、fig-xgzp-sensor.png（xgzp_p3）、fig-devkit-sch.png（ESP32/S3-N16R8原理图.png）、fig-handes-pcb.png（handes_p2 选清晰者）、fig-dmm-check.png（dmm.png）、fig-solder-check.png（solder_check.png）——每图 ls 校验非零
- [ ] 提交 `feat(book): 资源/ 纳编——bib 10 条+器件图规范化 7 张入 figures`

### Task 2: 六章增补（文字+图+cite）
- [ ] ch2：阀选型节（0520D vs 0520F 对照表+2 图+规格书引+P_min -53.3kPa 闭环句）；XGZP 量程句补图
- [ ] ch3：开发板对照节（DevKitC-1 图+strapping/电源/USB 三处对照表——素材取 spec pcb-design §2.1 审计结论）
- [ ] ch5：供应链节（汉戴斯实拍+B2B 平替叙事）；散件清点图
- [ ] ch6：官方 3MF S/M/L 尺寸对照表（从 3MF 文件名+目录归纳，不打开模型——尺寸从 FlowIO 官方文档 GUI/产品页文字取，无据则列表仅列模块名不列尺寸）
- [ ] ch1：官方 GUI 参照引注+mp4 场景转述（一段文字）；ch9 同步引注句
- [ ] ch13 下篇：预置 A201/A202 现场图位（\includegraphics 已就位+caption 注"实拍示例，验收时替换"）
- [ ] 版权纪律自查：grep 官方源码摘录=0（只允许接口签名行）
- [ ] xelatex+biber 零错、报页数 → 提交 `feat(book): 六章增补实物级素材 (阀对照/开发板对照/供应链/3MF 对照/验收图位)`

### Task 3: 外部参考清理（**仅执行用户批准档**）
- [ ] 档 A（零风险 16.4G）：删 freerouting-src/、fr-src.tar.gz、jdk-21/、jre.zip、jre25.zip
- [ ] 档 B（谨慎 ~1.5G，删前 grep BRINGUP/specs 确认无路径依赖后执行）：KiCadRoutingTools-main/.git、艾谷 4_Program+node_modules
- [ ] 每档删后 du -sh 汇总释放量；HANDOFF.md 记录（保留清单：jar/jdk25/KRT 工作区/艾谷 PDF+PPT/kicad-libs/papers）
- [ ] 提交 HANDOFF 更新

## 完成定义
spec §4 三条：bib/增补/图落位且编译零错；删除仅按批准档执行且记录释放量。
