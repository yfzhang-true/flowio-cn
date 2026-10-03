# -*- coding: utf-8 -*-
"""consistency_check.py — 书稿×真源 机器一致性检查器（stdlib，纯只读）。

四类机器检查（spec 2026-10-03-book-code-consistency-design.md §3）：
  1. 常数核对   check_constants —— 真源常数（12 项核对表）在指定章文件出现；
                数字允许末位补零差（14 == 14.0），不允许有效位漂移（3.269 != 3.27），
                允许中文/LaTeX 单位邻接。
  2. 路径存在性 check_paths    —— \\texttt{...} 含 "/" 的 token 按仓库多根解析存在性
                （URL/邮箱/glob 通配进白名单）。
  3. cite 键差  check_cites    —— 书稿 \\cite 键集合 vs reference.bib 键集合，双向差。
  4. 代码片段   check_snippets —— 按 SNIPPETS 映射从真源提取函数体/块（大括号/缩进计数），
                规范化（去空白/去注释行）后断言书稿 lstlisting 含其首尾各 5 行（逐行子串）。

用法：  python consistency_check.py            # 跑真实书稿，输出 findings，非零退出
        python test_consistency_check.py      # fixture 红绿测试
书骗人比代码错更严重——本工具只做机器可判定的部分，语义漂移交 AI 审计（Task 2）。
"""
import os
import re
import sys
import glob as _glob
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]          # E:/FLOWIO

HEAD_TAIL = 5                                       # 首尾各 5 行断言窗口


class Finding(object):
    __slots__ = ("kind", "where", "msg")

    def __init__(self, kind, where, msg):
        self.kind, self.where, self.msg = kind, where, msg

    def __str__(self):
        return "[%s] %s: %s" % (self.kind, self.where, self.msg)


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------- 规范化 ----
def strip_comments(text, lang):
    """按语言去注释与 docstring（宽松：不解析字符串字面量）。lang: py | c | js | None"""
    if lang == "py":
        text = re.sub(r'"""(?:"""|.)*?"""', " ", text, flags=re.S)   # docstring 视同注释
        text = re.sub(r"'''[^']*?'''", " ", text, flags=re.S)
        text = re.sub(r"#.*", "", text)
    elif lang in ("c", "js"):
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        text = re.sub(r"//[^\n]*", "", text)
    return text


def norm_lines(text, lang=None):
    """规范化为非空行列表：去注释、行内空白折叠、去首尾空白与空行。"""
    out = []
    for ln in strip_comments(text, lang).splitlines():
        ln = re.sub(r"\s+", " ", ln).strip()
        if ln:
            out.append(ln)
    return out


# ---------------------------------------------------------------- 章文件 ----
def resolve_tex(patterns, base):
    """章 glob 模式 -> 排序去重的文件绝对路径列表。"""
    files = []
    for pat in patterns:
        files.extend(sorted(_glob.glob(os.path.join(str(base), pat.replace("/", os.sep)))))
    seen, out = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def listings_of(tex_text):
    """提取 lstlisting 环境体列表（选项用括号配平扫描，支持跨行 caption）。"""
    bodies = []
    for m in re.finditer(r"\\begin\{lstlisting\}", tex_text):
        i = m.end()
        # 跳过可选参数 [...]（配平计数）
        if i < len(tex_text) and tex_text[i] == "[":
            depth, j = 1, i + 1
            while j < len(tex_text) and depth:
                if tex_text[j] == "[":
                    depth += 1
                elif tex_text[j] == "]":
                    depth -= 1
                j += 1
            i = j
        end = tex_text.find(r"\end{lstlisting}", i)
        if end < 0:
            break
        bodies.append(tex_text[i:end])
    return bodies


def equations_of(tex_text):
    """提取 equation/align 环境体列表。"""
    out = []
    for env in ("equation", "equation*", "align", "align*"):
        for m in re.finditer(r"\\begin\{" + env + r"\}(.*?)\\end\{" + env + r"\}", tex_text, re.S):
            out.append(m.group(1))
    return out


def tex_flat(tex_text):
    """整页规范化文本（去 LaTeX 空距宏 + 折叠空白），用于常数匹配。"""
    t = tex_text
    t = re.sub(r"\\[,;!]", "", t)
    t = re.sub(r"\\(quad|qquad|,)\b", "", t)
    return re.sub(r"\s+", "", t)


# ================================================================ 1. 常数 ===
def _num_re(v):
    """常数串 -> 匹配正则。数字：词边界 + 末位允许补零；十六进制/uuid：词边界。"""
    if re.fullmatch(r"[0-9a-fA-Fx]+", v) and ("x" in v or any(c in v for c in "abcdef")):
        return re.compile(r"(?<![0-9a-zA-Z])" + re.escape(v) + r"(?![0-9a-fA-F])", re.I)
    if re.fullmatch(r"\d+", v):
        return re.compile(r"(?<![\d.])" + re.escape(v) + r"(\.0*)?(?!\d)")
    if re.fullmatch(r"\d+\.\d+", v):
        head, frac = v.split(".")
        return re.compile(r"(?<![\d.])" + re.escape(head) + r"\." + re.escape(frac) + r"0*(?!\d)")
    return re.compile(r"(?<![0-9a-zA-Z])" + re.escape(v))


def check_constants(entries, base):
    """entries: (名称, [可接受变体], [章 glob 模式])。常数缺章/缺值 -> finding（每常数一条）。"""
    findings = []
    for name, variants, patterns in entries:
        files = resolve_tex(patterns, base)
        if not files:
            findings.append(Finding("const", name,
                                    "章文件不存在（按模式 %s）" % ", ".join(patterns)))
            continue
        flats = [(os.path.relpath(f, base), tex_flat(_read(f))) for f in files]
        hit = any(_num_re(v).search(t) for v in variants for _, t in flats)
        if not hit:
            where = ", ".join(fn for fn, _ in flats)
            shown = " 或 ".join(variants)
            findings.append(Finding("const", where,
                                    "常数 %s（%s）未在指定章出现" % (name, shown)))
    return findings


# 真源常数核对表（plan Task1 原文 12 项；值以仓库当前实现为真源）
CONSTANTS = [
    ("vout",        ["3.269"],                        ["book/content/ch02*.tex"]),
    ("tau_ms",      ["1.79"],                         ["book/content/ch02*.tex", "book/content/ch09*.tex"]),
    ("r_coil",      ["14"],                           ["book/content/ch02*.tex"]),
    ("crc_poly",    ["0x07"],                         ["book/content/ch08*.tex", "book/content/ch10*.tex"]),
    ("uuid_base",   ["f10a5c00"],                     ["book/content/ch08*.tex"]),
    ("valve_gpio",  ["4/5/6/7/10/11/12/21", "4,5,6,7,10,11,12,21"],
                                                      ["book/content/ch07*.tex"]),
    ("gamma",       ["1.2"],                          ["book/content/ch00b*.tex"]),
    ("orifice",     ["114.5"],                        ["book/content/ch00b*.tex"]),
    ("fee_low",     ["360"],                          ["book/content/ch05*.tex"]),
    ("fee_high",    ["720"],                          ["book/content/ch05*.tex"]),
    ("explode_disp", ["10"],                          ["book/content/ch13*.tex"]),   # 计划原文指向 ch13（现书稿无此章）
    ("test_count",  ["33"],                           ["book/content/ch07*.tex"]),
]

# \texttt 路径 token 的仓库解析根（书稿常以子仓库相对路径书写）
PATH_ROOTS = ["", "book/", "book/content/", "book/figures/", "book/tickets/", "book/tools/",
              "firmware/", "firmware/components/", "firmware/components/pn_core/src/",
              "firmware/components/pn_core/include/",
              "firmware/main/", "firmware/twin/", "firmware/twin/webapp/",
              "firmware/twin/webapp/js/", "firmware/tests/",
              "hardware/flowio-p1/", "hardware/flowio-p1/tools/",
              "hardware/flowio-p1/enclosure/", "hardware/flowio-p1/fab/",
              "hardware/flowio-p1/sch/",
              "sdk/python/", "sdk/python/flowio_sdk/", "literature/", "docs/"]

# 路径形态判定：段字符合法 + （含扩展名段 或 首段是已知目录名）
_KNOWN_DIRS = {"book", "content", "figures", "tickets", "tools", "data",
               "firmware", "components", "pn_core", "pn_hal_esp32", "main", "tests",
               "twin", "webapp", "js", "sdk", "python", "flowio_sdk",
               "hardware", "flowio-p1", "enclosure", "fab", "sch",
               "literature", "docs", "src", "examples", "lib", "meshes", "flows"}
_SEG_RE = re.compile(r"^[\w][\w.+-]*$")


def _is_pathlike(tok):
    """URL/端点/命令/数学记号等非文件路径排除，仅保留像仓库路径的 token。"""
    if tok.startswith(("/", ".")) or re.search(r"""[\s\\?=\[\]*'"@#%]""", tok):
        return False
    segs = [s for s in tok.split("/") if s]
    if len(segs) < 2 or not all(_SEG_RE.match(s) for s in segs):
        return False
    if any(re.fullmatch(r"[\d.]+", s) for s in segs):       # dtr/rts、load_a/3.0 等
        return False
    return any("." in s for s in segs[1:]) or segs[0] in _KNOWN_DIRS


# ================================================================ 2. 路径 ===
def _clean_texttt(tok):
    tok = tok.replace(r"\_", "_").replace(r"\&", "&").replace(r"\%", "%")
    tok = tok.replace(r"\#", "#").replace(r"\$", "$")
    return tok.strip(" \t。，,.;；:：)）]】\"'")


def check_paths(tex_text, base, roots=None):
    """\\texttt{...} 含 / 的 token -> 仓库相对路径存在性；URL/非路径 token 进白名单。"""
    roots = PATH_ROOTS if roots is None else roots
    findings = []
    for m in re.finditer(r"\\texttt\{([^}]*)\}", tex_text):
        tok = _clean_texttt(m.group(1)).rstrip("/")
        if "/" not in tok or not _is_pathlike(tok):
            continue
        hit = any(os.path.exists(os.path.join(str(base), r, tok.replace("/", os.sep)))
                  for r in roots)
        if not hit:
            findings.append(Finding("path", tok,
                                    "仓库中不存在该路径: %s（%d 个根下均未命中）" % (tok, len(roots))))
    return findings


# ================================================================ 3. cite ====
_CITE_RE = re.compile(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")
_BIBKEY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,")


def check_cites(tex_files, bib_path):
    """书稿 \\cite 键集合 vs bib 键集合，双向差各一条 finding。"""
    cited, bibbed = set(), set()
    for tf in tex_files:
        for grp in _CITE_RE.findall(_read(tf)):
            for k in grp.split(","):
                k = k.strip()
                if k:
                    cited.add(k)
    if os.path.exists(bib_path):
        bibbed = set(_BIBKEY_RE.findall(_read(bib_path)))
    findings = []
    where = os.path.basename(str(bib_path))
    for k in sorted(cited - bibbed):
        findings.append(Finding("cite", where, "书稿引用的键不在 bib 中: %s" % k))
    for k in sorted(bibbed - cited):
        findings.append(Finding("cite", where, "bib 孤立键（未被任何章引用）: %s" % k))
    return findings


# ================================================================ 4. 片段 ====
def _extract_block(src_lines, start_marker, end_marker):
    """[start_marker 行 .. end_marker 行(含)]；无 end_marker 时取 60 行上限。"""
    s = next((i for i, ln in enumerate(src_lines) if start_marker in ln), None)
    if s is None:
        return None
    if end_marker:
        e = next((i for i in range(s, len(src_lines)) if end_marker in src_lines[i]), None)
        if e is None:
            return None
        return src_lines[s:e + 1]
    return src_lines[s:s + 60]


_C_DEF = re.compile(r"^[A-Za-z_][\w\s\*]*?\b(\w+)\s*\(")
_PY_DEF = re.compile(r"^(\s*)(?:def|class)\s+(\w+)")


def _extract_func(src_lines, name, lang):
    """定位 def/class/C 函数定义行，按缩进（py）或大括号配平（c/js）取函数体。"""
    if lang == "py":
        for i, ln in enumerate(src_lines):
            m = _PY_DEF.match(ln)
            if m and m.group(2) == name:
                indent = len(m.group(1))
                body = [ln]
                for ln2 in src_lines[i + 1:]:
                    if ln2.strip() and (len(ln2) - len(ln2.lstrip())) <= indent:
                        break
                    body.append(ln2)
                return body
        return None
    for i, ln in enumerate(src_lines):
        if ln.startswith((" ", "\t")) or ("=" in ln and "=" in ln.split("(")[0]):
            continue
        m = _C_DEF.match(ln)
        if m and m.group(1) == name:
            body, depth, started = [], 0, False
            for ln2 in src_lines[i:]:
                body.append(ln2)
                for ch in ln2:
                    if ch == "{":
                        depth += 1
                        started = True
                    elif ch == "}":
                        depth -= 1
                if started and depth <= 0:
                    break
                if not started and len(body) > 8:
                    return None
            return body
    return None


def check_snippets(mapping, base):
    """mapping 条目: (章 glob, 真源相对路径|None, kind, 锚, lang)。

    kind: func(锚=函数/类名) | block(锚=(起始子串, 结束子串)) |
          equation(锚=方程环境须含的子串) | tokens(锚=须出现在真源的 token 元组)
    断言：真源片段规范化后首尾各 5 行，逐行是书稿 lstlisting 规范化行的子串。
    """
    findings = []
    for tex_glob, src_rel, kind, anchor, lang in mapping:
        tex_files = resolve_tex([tex_glob], base)
        if not tex_files:
            findings.append(Finding("snippet", tex_glob, "章文件不存在"))
            continue
        book_lines = []
        for tf in tex_files:
            for body in listings_of(_read(tf)):
                book_lines.extend(norm_lines(body, lang))
        if kind == "equation":
            all_eq = "\n".join(eq for tf in tex_files for eq in equations_of(_read(tf)))
            if re.sub(r"\s+", "", all_eq).find(re.sub(r"\s+", "", str(anchor))) < 0:
                findings.append(Finding("snippet", tex_glob,
                                        "方程环境中未找到锚点 %r" % anchor))
            continue

        src_path = os.path.join(str(base), src_rel.replace("/", os.sep)) if src_rel else None
        if src_rel and not os.path.exists(src_path):
            findings.append(Finding("snippet", src_rel, "真源文件不存在"))
            continue

        if kind == "tokens":
            src_flat = re.sub(r"\s+", "", _read(src_path))
            for tok in anchor:
                if re.sub(r"\s+", "", tok) not in src_flat:
                    findings.append(Finding("snippet", src_rel,
                                            "书稿用法 token 在真源中不存在: %s" % tok))
            continue

        src_lines = _read(src_path).splitlines()
        if kind == "func":
            body = _extract_func(src_lines, anchor, lang)
            label = "%s:%s" % (src_rel, anchor)
        else:
            body = _extract_block(src_lines, anchor[0], anchor[1])
            label = "%s:%s.." % (src_rel, anchor[0][:24])
        if not body:
            findings.append(Finding("snippet", src_rel, "真源锚点未定位到: %r" % (anchor,)))
            continue

        frag = norm_lines("\n".join(body), lang)
        want = frag[:HEAD_TAIL] + frag[-HEAD_TAIL:]
        # 书稿侧合并成单个规范化串：同时容忍书稿的并 行 与折 行（宽松匹配）
        book_flat = " ".join(book_lines)
        missing = [ln for ln in want if ln not in book_flat]
        if missing:
            shown = " && ".join(m[:60] for m in missing[:3])
            findings.append(Finding("snippet", tex_glob,
                                    "书稿列表与真源 %s 漂移（首尾%d行缺失 %d 行）: %s"
                                    % (label, HEAD_TAIL, len(missing), shown)))
    return findings


# 书稿代码列表映射（14 章中带真源代码的 12+ 处；plan Task1 原文清单）
SNIPPETS = [
    # ch00b 孔口方程环境（文献公式转录）
    ("book/content/ch00b*.tex", None, "equation", "114.5", None),
    # ch02 dP/dt 物理积分块（twin_api.c）与 BOARD 参数区（board_model.py）
    ("book/content/ch02*.tex", "firmware/twin/twin_api.c", "block",
     ("float V = V_MANIFOLD_L", "SENSOR_SPAN_KPA) p = -SENSOR_SPAN_KPA;"), "c"),
    ("book/content/ch02*.tex", "firmware/twin/board_model.py", "block",
     ("BOARD_PARAMS = {", "BUCK_EFF = 0.876"), "py"),
    # ch05 make_bom 段（mpn_of 起至交叉验证打印）
    ("book/content/ch05*.tex", "hardware/flowio-p1/tools/make_bom.py", "block",
     ("def mpn_of(pt):", "交叉验证: BOM"), "py"),
    # ch06 尺寸链参数区（make_case.py）与坐标映射证伪（make_meshes.py）
    ("book/content/ch06*.tex", "hardware/flowio-p1/enclosure/make_case.py", "block",
     ("WALL, CLR = 2.4, 0.5", "TY = 68.5"), "py"),
    ("book/content/ch06*.tex", "hardware/flowio-p1/enclosure/make_meshes.py", "func",
     "verify_mapping", "py"),
    # ch07 tca_encode 与 pn_cmd_feed
    ("book/content/ch07*.tex", "firmware/components/pn_core/src/tca9548.c", "func",
     "tca_encode", "c"),
    ("book/content/ch07*.tex", "firmware/main/main.c", "func", "pn_cmd_feed", "c"),
    # ch08 state_pack（含 unpack 头部至保留字节校验）
    ("book/content/ch08*.tex", "firmware/components/pn_core/src/ble_frame.c", "block",
     ("int ble_state_pack", "保留字节非 0"), "c"),
    # ch09 uGain 映射（flows.js）与关断续流（board_model.py）
    ("book/content/ch09*.tex", "firmware/twin/webapp/js/flows.js", "block",
     ("const gain = st.connected", "uSpeed.value = 0.6 + 2.2 * L.live01;"), "js"),
    ("book/content/ch09*.tex", "firmware/twin/board_model.py", "block",
     ('tau_on = p["l_coil"]', "self.i[k] = i if i > 0.0 else 0.0"), "py"),
    # ch10 crc8 与 encode 全函数
    ("book/content/ch10*.tex", "sdk/python/flowio_sdk/protocol.py", "func", "crc8", "py"),
    ("book/content/ch10*.tex", "sdk/python/flowio_sdk/protocol.py", "func", "encode", "py"),
    # ch11 ticket 用法（子命令 token 须存在于 ticket.py）
    ("book/content/ch11*.tex", "book/tools/ticket.py", "tokens",
     ("new", "report", "set_status"), None),
]


# ================================================================ 汇总 ======
def run_all(base=REPO, constants=None, snippets=None, cites=True, paths=True):
    base = str(base)
    findings = []
    findings += check_constants(constants if constants is not None else CONSTANTS, base)
    if snippets is not None:
        findings += check_snippets(snippets, base)
    else:
        findings += check_snippets(SNIPPETS, base)
    if cites:
        tex_files = sorted(_glob.glob(os.path.join(base, "book", "content", "*.tex")))
        findings += check_cites(tex_files, os.path.join(base, "book", "reference.bib"))
    if paths:
        for tf in sorted(_glob.glob(os.path.join(base, "book", "content", "*.tex"))):
            findings += check_paths(_read(tf), base)
    return findings


def main(argv=None):
    findings = run_all()
    by_kind = {}
    for f in findings:
        by_kind.setdefault(f.kind, []).append(f)
    print("=" * 72)
    print("consistency_check — 书稿×真源 机器一致性 (base=%s)" % REPO)
    print("=" * 72)
    for kind in ("const", "path", "cite", "snippet"):
        items = by_kind.get(kind, [])
        print("\n[%s] %d 项发现" % (kind, len(items)))
        for f in items:
            print("  " + str(f))
    total = len(findings)
    print("\n合计 %d 项发现 (const=%d path=%d cite=%d snippet=%d)"
          % (total, len(by_kind.get("const", [])), len(by_kind.get("path", [])),
             len(by_kind.get("cite", [])), len(by_kind.get("snippet", []))))
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
