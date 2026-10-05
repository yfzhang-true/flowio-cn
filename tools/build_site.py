# -*- coding: utf-8 -*-
"""build_site — 生成 GitHub Pages 静态演示站 (site/) 从孪生 webapp 源.

用法: python tools/build_site.py   (在仓库根执行; 幂等, 重跑覆盖)

步骤:
  1. 同步 firmware/twin/webapp/{index.html,css,js,vendor,flows.json,hotspots.json} → site/
  2. 拷贝 firmware/twin/meshes/*.stl → site/meshes/; assembly.json → site/data/ (路径改写)
  3. 路径改写: "/webapp/"→"", "/meshes/"→"meshes/" (Pages 子路径 /flowio-cn/ 兼容)
  4. index.html 注入 demo_api.js + sim_demo.js (classic script, 先于 ES modules)
  5. 生成 site/js/sim_test_data.json (Python sim_engine 默认工况, 供 JS 对拍)
  6. 写 .nojekyll; 安全断言 (无密钥模式/无简历/无超大文件)
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # 仓库根
SRC = ROOT / "firmware" / "twin"
WEB = SRC / "webapp"
SITE = ROOT / "site"

SECRET_PAT = re.compile(r"ghp_[A-Za-z0-9]{20,}|mcpk2_[A-Za-z0-9_-]{10,}")


def rewrite(text: str) -> str:
    text = text.replace('"/webapp/', '"')
    text = text.replace('"/meshes/', '"meshes/')
    # import map 的地址必须是合法 URL (./ ../ / 开头); 通用剥前缀后产生的裸值
    # "vendor/..." 会被浏览器判 null -> three 解析失败 (2026-10-03 事故第三层)
    text = text.replace('"three":"vendor/', '"three":"./vendor/')
    return text


def rewrite_js(text: str) -> str:
    """js 模块专用: ES import 裸说明符修正 ("js/x.js" 不走相对解析, 必须改 ./x.js).
    注意: import 修正必须先于通用 rewrite, 否则 "/webapp/" 先被剥掉导致匹配不到.
    覆盖三种形态: 静态 from "..." / 副作用 import "..." / 动态 import("...")——
    动态 import 常为惰性加载 (scene.js/flows.js), 静态扫描看不见, 生产才炸 (2026-10-03 事故).
    M4 组件化后 js/components/*.js 互相全用 ./ ../ 相对路径 + "three" 裸说明符
    (importmap 解析) —— 相对路径无需改写即可在 site/ 同构工作, 本函数保持幂等."""
    text = text.replace('from "/webapp/js/', 'from "./')
    text = text.replace('import "/webapp/js/', 'import "./')
    text = text.replace('import("/webapp/js/', 'import("./')
    # vendor: js/ 下模块引 /site/vendor/ 需上一级 "../vendor/"
    text = text.replace('from "/webapp/vendor/', 'from "../vendor/')
    text = text.replace('import "/webapp/vendor/', 'import "../vendor/')
    text = text.replace('import("/webapp/vendor/', 'import("../vendor/')
    return rewrite(text)


def main() -> int:
    # ---------- 1/2. 目录与拷贝
    # M4: js/components/ 子目录 (组件文件互相 ./ ../ 相对引用, 拷贝后无需改写)
    for sub in ("css", "js", "js/components", "vendor", "meshes", "data"):
        (SITE / sub).mkdir(parents=True, exist_ok=True)
    # D4 (2026-10-05): connections 渲染数据 (折线 payload + 真值原文副本) 随站同步
    for name in ("flows.json", "hotspots.json", "connections_scene.json", "connections.json"):
        shutil.copyfile(WEB / name, SITE / name)
    for f in (WEB / "css").glob("*"):
        if f.is_file():
            (SITE / "css" / f.name).write_bytes(rewrite(f.read_text(encoding="utf-8")).encode("utf-8"))
    for f in (WEB / "js").glob("*.js"):
        (SITE / "js" / f.name).write_bytes(rewrite_js(f.read_text(encoding="utf-8")).encode("utf-8"))
    for f in (WEB / "js" / "components").glob("*.js"):
        (SITE / "js" / "components" / f.name).write_bytes(
            rewrite_js(f.read_text(encoding="utf-8")).encode("utf-8"))
    if (SITE / "js" / "demo_api.js").exists() is False:
        print("!! 缺少 site/js/demo_api.js (应先由仓库提供, 不从 webapp 同步覆盖)")
    # vendor 含子目录 (addons/), 必须整树拷贝 —— 顶层 glob 会漏 addons 导致
    # scene.js 的 ../vendor/addons/*.js 全 404, 动态 import 整图失败 (2026-10-03 事故第二层)
    shutil.copytree(WEB / "vendor", SITE / "vendor", dirs_exist_ok=True)
    # 旧版已拆解文件 (panels/simlab 迁入组件) 残影清除, 防 site 留尸
    for stale in ("panels.js", "simlab.js"):
        stale_path = SITE / "js" / stale
        if stale_path.exists():
            stale_path.unlink()
    n_stl = 0
    for f in (SRC / "meshes").glob("*.stl"):
        shutil.copyfile(f, SITE / "meshes" / f.name)
        n_stl += 1

    # assembly.json → data/ (stl 路径改写)
    asm = json.loads((SRC / "meshes" / "assembly.json").read_text(encoding="utf-8"))
    for part in asm.get("parts", []):
        if isinstance(part.get("stl"), str):
            part["stl"] = part["stl"].replace("/meshes/", "meshes/")
    (SITE / "data" / "assembly.json").write_bytes(
        json.dumps(asm, ensure_ascii=False).encode("utf-8"))

    # ---------- 3/4. index.html: 改写 + 注入 demo 脚本
    html = (WEB / "index.html").read_text(encoding="utf-8")
    html = rewrite(html)
    inject = ('<script src="js/sim_demo.js"></script>\n'
              '<script src="js/demo_api.js"></script>\n')
    marker = '<script type="importmap">'
    if "demo_api.js" not in html:
        html = html.replace(marker, inject + marker, 1)
    (SITE / "index.html").write_bytes(html.encode("utf-8"))
    (SITE / ".nojekyll").write_bytes(b"")

    # ---------- 5. sim 对拍数据 (Python 权威输出)
    sys.path.insert(0, str(SRC))
    import sim_engine  # noqa: E402
    cases = {}
    for c in ("buck", "dior", "valve", "i2c"):
        r = sim_engine.run(c, {})
        cases[c] = {"params": r["params"],
                    "metrics": [{"name": m["name"], "value": m["value"]} for m in r["metrics"]]}
    (SITE / "js" / "sim_test_data.json").write_bytes(
        json.dumps(cases, ensure_ascii=False).encode("utf-8"))

    # ---------- 6. 安全断言
    bad = []
    for f in SITE.rglob("*"):
        if not f.is_file():
            continue
        if f.stat().st_size > 8 * 1024 * 1024:
            bad.append(f"超大文件: {f.relative_to(SITE)} ({f.stat().st_size/1e6:.1f}MB)")
        if f.suffix in (".js", ".json", ".html", ".css", ".txt", ""):
            data = f.read_bytes()
            if SECRET_PAT.search(data.decode("utf-8", errors="ignore")):
                bad.append(f"疑似密钥: {f.relative_to(SITE)}")
            if b"\xe7\xae\x80\xe5\x8e\x86" in data:  # "简历" UTF-8
                bad.append(f"含简历字样: {f.relative_to(SITE)}")
    if bad:
        print("安全断言失败:")
        for b in bad:
            print("  -", b)
        return 1

    n_js = len(list((SITE / "js").glob("*.js"))) + len(list((SITE / "js" / "components").glob("*.js")))
    print(f"SITE OK: index.html + js×{n_js} (含 components/) + stl×{n_stl} + assembly + sim_test_data, "
          f"共 {sum(1 for _ in SITE.rglob('*') if _.is_file())} 文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
