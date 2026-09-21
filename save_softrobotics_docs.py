"""Save the FlowIO soft-robotics documentation (softrobotics.io) locally
as Markdown files + images + linked assets.

FlowIO here is Ali Shtarbanov's pneumatic development platform for soft
robotics (MIT Media Lab, CHI'21) - NOT the flow-cytometry FlowIO library.

Usage:
    D:/MiniConda/envs/paper20-cu128/python.exe save_softrobotics_docs.py

Output: E:/FLOWIO/flowio-softrobotics-docs/
"""

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import html2text

BASE = "https://www.softrobotics.io/"
IMG_HOST = "static.wixstatic.com"
OUT = Path(r"E:\FLOWIO\flowio-softrobotics-docs")
IMG_DIR = OUT / "images"

# doc pages in site menu order: (url_path, nav_title)
PAGES = [
    ("introduction", "Introduction"),
    ("documentation", "Documentation Overview"),
    ("gui-overview", "GUI Overview"),
    ("gui", "Launch GUI"),
    ("auto-off", "Auto Power OFF"),
    ("battery-charging", "Battery Charging"),
    ("pneumatic-configurations", "Pneumatic Configurations"),
    ("external-air-supply", "External Air Supply"),
    ("latency-and-delays", "Latency & Delays"),
    ("more-than-5-ports", "More Than 5 Ports"),
    ("software-stack", "Software Stack"),
    ("arduino-api", "Arduino API"),
    ("premium-content", "Premium / IoT Features"),
    ("limitations", "Limitations"),
    ("about", "About"),
    ("chi22", "CHI'22 Paper Page"),
    ("dis23", "DIS'23 Paper Page"),
    ("fab24", "FAB24 Paper Page"),
]

# homepage PDF skipped: byte-identical to the CHI'21 paper already saved
# in E:\FLOWIO (verified by md5 on 2026-09-19)

CC_BANNER = "FlowIO is provided under a Creative Commons"


def guard(url: str, allowed: str) -> str:
    """Server-side URL request guard: https + exact allowed public host only."""
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if p.scheme != "https" or host != allowed:
        raise ValueError(f"blocked non-allowed URL: {url}")
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or re.match(
        r"^(10\.|127\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.)", host
    ):
        raise ValueError(f"blocked private/loopback host: {url}")
    return url


SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0 (flowio-docs-saver)"


def clean_main(soup: BeautifulSoup) -> BeautifulSoup.find:
    for tag in soup.find_all(["script", "style", "noscript", "svg"]):
        tag.decompose()
    main = soup.find("main") or soup.body
    # side menu: walk up from the /introduction anchor to the small container
    # holding the whole nav (>=5 links, signature text, under 1000 chars)
    for a in main.find_all("a", href=re.compile(r"softrobotics\.io/introduction$")):
        comp = a.parent
        while comp is not None and comp.name is not None:
            txt = comp.get_text()
            if len(txt) > 1000:  # walked past the menu into page content
                break
            if ("Software Stack" in txt
                    and len(comp.find_all("a", href=True)) >= 5):
                comp.decompose()
                break
            comp = comp.parent
        break
    # JS-driven anchors without a real href (leftover menu entries)
    for a in main.find_all("a"):
        href = (a.get("href") or "").strip()
        if not href or href in ("#", "javascript:;") or href.startswith("./#"):
            a.decompose()
    # repeated CC-license banner component
    for node in main.find_all(string=lambda t: t and CC_BANNER in t):
        comp = node.find_parent("div", id=re.compile(r"^comp-"))
        if comp:
            comp.decompose()
    return main


def page_markdown(path: str, nav_title: str, html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else path
    title = re.sub(r"\s*\|\s*SoftRobotics\.IO\s*$", "", title) or path

    main = clean_main(soup)

    # pull code blocks out (same trick as the FCS saver)
    code_blocks = []
    for pre in main.find_all("pre"):
        code_blocks.append("```\n" + pre.get_text().rstrip() + "\n```")
        pre.replace_with(f"@@CODEBLOCK{len(code_blocks) - 1}@@")

    # localize wixstatic images
    n_img = 0
    for i, img in enumerate(main.find_all("img")):
        src = (img.get("src") or "").strip()
        if not src.startswith("https://"):
            continue
        if (urlparse(src).hostname or "").lower() != IMG_HOST:
            continue
        name = f"{path}_{i}_" + re.sub(r"[^A-Za-z0-9._-]", "_", src.split("/")[-1].split("?")[0])
        dest = IMG_DIR / name
        if not dest.exists():
            dest.write_bytes(SESSION.get(guard(src, IMG_HOST), timeout=60).content)
        img["src"] = f"images/{name}"
        n_img += 1

    md = H2T.handle(str(main))
    for i, block in enumerate(code_blocks):
        md = md.replace(f"@@CODEBLOCK{i}@@", block)
    md = md.replace("\u200b", "")
    # drop per-page repeated boilerplate paragraph
    paras = md.split("\n\n")
    md = "\n\n".join(p for p in paras if "There is much more documentation" not in p
                     and "consider volunteering" not in p)
    # drop leading heading that just repeats the page title
    names = {re.sub(r"\s+", " ", t).strip().lower() for t in (nav_title, title)}
    md = re.sub(r"^\s*#+\s*[^\n]*?\n+", lambda m: "" if re.sub(
        r"[#*\s]", "", m.group(0)).strip().lower() in
        {re.sub(r"[*\s]", "", n) for n in names} else m.group(0), md, count=1)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    return title, md


H2T = html2text.HTML2Text()
H2T.body_width = 0
H2T.single_line_break = False
H2T.ignore_emphasis = False


def main() -> int:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    saved = []

    for path, nav_title in PAGES:
        url = f"{BASE}{path}"
        try:
            resp = SESSION.get(guard(url, "www.softrobotics.io"), timeout=60)
            resp.raise_for_status()
        except Exception as e:
            print(f"  ! failed {path}: {e}")
            continue
        title, md = page_markdown(path, nav_title, resp.text)
        dest = OUT / f"{path}.md"
        dest.write_text(f"# {nav_title}\n\n> Source: {url}\n\n{md}", encoding="utf-8")
        saved.append((path, nav_title, dest))
        print(f"  saved {dest.name:28} ({len(md):6,} chars)")

    # README index
    lines = [
        "# FlowIO（软体机器人气动平台）本地文档",
        "",
        "FlowIO = Ali Shtarbanov（MIT Media Lab）开发的软体机器人气动开发平台，",
        f"官方文档站 <{BASE}>（Wix 站点，2026-09-19 抓取转换为 Markdown）。",
        "",
        "| 本地文件 | 内容 |", "| --- | --- |",
    ]
    for path, nav_title, _ in saved:
        lines.append(f"| `{path}.md` | {nav_title} |")
    lines += [
        "",
        "补充材料：",
        "- `arduino-library-readmes/` — GitHub 上 FlowIO Arduino 库的 README（API 文档入口，固件等高层代码在私有仓库需申请）",
        "- `images/` — 页面配图（含气动配置、GUI 截图等）",
        "- 论文：`E:\\FLOWIO\\FlowIO Development Platform – the Pneumatic \"Raspberry Pi\"for Sof Robotics.pdf`（CHI 2021，"
        "与官网首页挂载的 PDF 为同一文件）",
        "",
        "未抓取（非文档内容）：商店/社区论坛/法律条款等页面。",
    ]
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    n_img = len(list(IMG_DIR.glob("*")))
    print(f"\nDone: {len(saved)}/{len(PAGES)} pages, {n_img} images -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
