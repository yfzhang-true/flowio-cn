# 项目根唯一入口整理实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。

**Goal:** 按 spec `2026-10-03-root-consolidation-design.md` 将 E:/FLOWIO-外部参考 并入 资源/工具链，清理根目录 2.3G 冗余，全部路径引用同步。

**Tech Stack:** mv/git rm --cached/.gitignore/xelatex+biber 复验

---

### Task 1: 迁移 1.6G 工具链 + 删源目录
- [ ] `mkdir -p 资源/工具链` → 7 项 mv（含短名重命名，照 spec §2 表逐条）
- [ ] 迁后 `rm -rf E:/FLOWIO-外部参考`（含根 README.md 一并吸收改写）
- [ ] `du -sh 资源/工具链` ≈1.6G 验证；`ls E:/FLOWIO-外部参考` → No such file

### Task 2: 路径引用同步（8 处 + grep 兜底）
- [ ] reference.bib 两处 howpublished 改新路径
- [ ] plan 2026-10-01-p1-auto-finish.md KRT 三处改新路径
- [ ] 资源/工具链/README.md 重写（从旧 README 迁移，路径列全改新；追加艾谷/papers/aeonlabs 行）
- [ ] `grep -rn "FLOWIO-外部参考" firmware/ book/ hardware/ sdk/ --include="*.py" --include="*.sh" --include="*.bib" --include="*.md"` 兜底清零（BRINGUP 若有同改）
- [ ] HANDOFF.md 追加路径迁移对照表（旧→新 7 行）
- [ ] xelatex+biber 两遍零错（bib 路径改后无 undefined）

### Task 3: 根目录与 git 索引清理（释放 ~2.3G 工作区 + git 瘦身）
- [ ] `rm FlowIO-Arduino-Libraries-master.zip`；`mv FlowIO-Arduino-Libraries-master 资源/官方参考/arduino-libraries`
- [ ] `git rm -r --cached firmware/build` + .gitignore 加 `/firmware/build/`（磁盘可留可删——删，idf 重编即得）
- [ ] `git rm -r --cached firmware/twin/deprecated/ml-leak/dataset`（306M 二进制）+ .gitignore 追加该行；磁盘保留（归档纪律）
- [ ] `mv lootdrop_call.py save_softrobotics_docs.py → study-notes/scripts/` 或 git rm（一次性脚本，选 git rm + 磁盘删）
- [ ] literature/ 检查：git ls-files literature/ | grep .pdf——若有则 git rm --cached（PDF 留磁盘，txt 在库）
- [ ] `git add -A && git commit -m "chore: 项目根唯一入口——外部参考并入资源/工具链(1.6G), build/deprecated出索引, 根散件归位"`

### Task 4: 全回归 + 终验
- [ ] 五套测试（webapp/classic×3/api_board）+ qemu 冒烟 + xelatex 零错
- [ ] spec §5 五条逐项打勾；HANDOFF 补一行"唯一入口达成"
- [ ] 终提交

## 完成定义 = spec §5
