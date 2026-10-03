# -*- coding: utf-8 -*-
"""consistency_check 的失败先行测试（TDD Step 1）。

四类检查各配红/绿 fixture（临时目录迷你书稿/真源，不触碰真实书稿）：
  1. 常数核对：真源 3.269 书稿写 3.27 -> 检出；写 3.269 -> 放行；14.0 对 14 -> 放行
  2. 路径存在性：书稿引不存在文件 -> 检出；URL -> 白名单跳过
  3. \\cite 键差：书稿引 bib 无键 -> 检出；bib 多余键 -> 检出（双向）
  4. 代码片段模糊匹配：去空白去注释后首尾 5 行子串断言，书稿改一行语义 -> 检出
"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import consistency_check as cc


def _write(root, rel, text):
    p = os.path.join(root, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


# ---------------------------------------------------------------- 1. 常数
def test_constants_rounding_drift_detected():
    with tempfile.TemporaryDirectory() as td:
        # 真源是 3.269（由真源/CONSTANTS 侧声明），书稿只写 3.27 -> 精度丢失，必须检出
        _write(td, "book/content/ch02-twin.tex", "输出 $3.27$\\,V。")
        fs = cc.check_constants([("vout", ["3.269"], ["book/content/ch02*.tex"])], td)
        assert any("vout" in f.msg for f in fs), fs


def test_constants_exact_pass():
    with tempfile.TemporaryDirectory() as td:
        _write(td, "book/content/ch02-twin.tex", "实测 $3.269$\\,V；线圈 $14\\,\\Omega$ 与 14.0 等值。")
        fs = cc.check_constants([("vout", ["3.269"], ["book/content/ch02*.tex"]),
                                 ("r_coil", ["14"], ["book/content/ch02*.tex"])], td)
        assert fs == [], fs


def test_constants_missing_file_is_finding():
    with tempfile.TemporaryDirectory() as td:
        fs = cc.check_constants([("explode_disp", ["10"], ["book/content/ch13*.tex"])], td)
        assert any("ch13" in f.msg for f in fs), fs


# ---------------------------------------------------------------- 2. 路径
def test_paths_missing_detected_url_skipped():
    with tempfile.TemporaryDirectory() as td:
        _write(td, "components/pn_core/src/cli.c", "/* x */")
        tex = (r"见 \texttt{components/pn_core/src/cli.c} 与 \texttt{src/missing.c}。"
               r"网页 \texttt{https://example.com/a.png} 不算路径。")
        fs = cc.check_paths(tex, td, roots=["", "components/"])
        assert len(fs) == 1 and "missing.c" in fs[0].msg, fs


# ---------------------------------------------------------------- 3. cite
def test_cites_bidirectional_diff():
    with tempfile.TemporaryDirectory() as td:
        tex = _write(td, "book/content/ch01.tex", r"引~\cite{GoodKey,GhostKey}。")
        bib = _write(td, "book/reference.bib",
                     "@article{GoodKey,\n  title={T},\n}\n@book{OrphanKey,\n  title={O},\n}\n")
        fs = cc.check_cites([tex], bib)
        msgs = " | ".join(f.msg for f in fs)
        assert "GhostKey" in msgs and "OrphanKey" in msgs, msgs


def test_cites_all_match_pass():
    with tempfile.TemporaryDirectory() as td:
        tex = _write(td, "book/content/ch01.tex", r"~\cite[p.~5]{A}~\cite{B,C}")
        bib = _write(td, "book/reference.bib", "@x{A,\nt={}}\n@x{B,\n}\n@x{C,\n}\n")
        assert cc.check_cites([tex], bib) == []


# ---------------------------------------------------------------- 4. 片段
PY_SRC = '''\
def alpha(vals):
    """加总。"""
    total = 0
    for v in vals:
        total = total + v
    return total


def beta():
    return 1
'''

def _mini_tex(body):
    return ("\\begin{lstlisting}[language=Python,\n  caption={demo}]\n"
            + body + "\\end{lstlisting}\n")


def test_snippet_verbatim_pass_and_drift_detected():
    with tempfile.TemporaryDirectory() as td:
        _write(td, "src/mod.py", PY_SRC)
        mapping = [("book/content/chX*.tex", "src/mod.py", "func", "alpha", "py")]
        texf = "book/content/chX.tex"

        good = _mini_tex("def alpha(vals):\n    total = 0\n    for v in vals:\n"
                         "        total = total + v\n    return total\n")
        _write(td, texf, good)
        assert cc.check_snippets(mapping, td) == []

        bad = _mini_tex("def alpha(vals):\n    total = 0\n    for v in vals:\n"
                        "        total = total - v\n    return total\n")
        _write(td, texf, bad)
        fs = cc.check_snippets(mapping, td)
        assert fs and "total = total + v" in fs[0].msg, [str(f) for f in fs]


def test_snippet_whitespace_and_comments_ignored():
    with tempfile.TemporaryDirectory() as td:
        csrc = ("int enc(int a)\n{\n    /* 头注释 */\n    int b = a + 1;\n"
                "    return b;   // 尾注释\n}\n")
        _write(td, "src/mod.c", csrc)
        mapping = [("book/content/chY*.tex", "src/mod.c", "func", "enc", "c")]
        tex = _mini_tex("int enc(int a)\n{\n  int b = a + 1;\n  return b;\n}\n")
        _write(td, "book/content/chY.tex", tex)
        assert cc.check_snippets(mapping, td) == []


def test_snippet_head_tail5_window():
    with tempfile.TemporaryDirectory() as td:
        # 体长 >10 行：改中间行（首尾 5 行窗外）-> 放行；改首行 -> 检出
        body = "\n".join("    x%d = %d" % (i, i) for i in range(12))
        src = "def big():\n" + body + "\n    return x0\n"
        _write(td, "src/big.py", src)
        mapping = [("book/content/chZ*.tex", "src/big.py", "func", "big", "py")]
        mid = "\n".join("    x%d = %d" % (i, 99 if i == 6 else i) for i in range(12))
        texf = "book/content/chZ.tex"
        _write(td, texf, _mini_tex("def big():\n" + mid + "\n    return x0\n"))
        assert cc.check_snippets(mapping, td) == []
        _write(td, texf, _mini_tex("def big():\n" + mid.replace("x0 = 0", "x0 = 7") + "\n    return x0\n"))
        fs = cc.check_snippets(mapping, td)
        assert fs and "x0 = 0" in fs[0].msg, [str(f) for f in fs]


def test_equation_and_tokens_kinds():
    with tempfile.TemporaryDirectory() as td:
        _write(td, "book/content/chT.tex",
               "\\begin{equation}\nQ = 114.5\\, u\\, C_v \\sqrt{\\Delta P}\n\\end{equation}\n")
        fs = cc.check_snippets([("book/content/chT*.tex", None, "equation", "114.5", None)], td)
        assert fs == [], fs
        fs = cc.check_snippets([("book/content/chT*.tex", None, "equation", "999.9", None)], td)
        assert fs, "方程环境缺锚点应检出"

        _write(td, "tools/cli.py", 'def main():\n    choices=("new", "report", "set_status")\n')
        tex = _mini_tex("python tools/cli.py new A1\nt  report\nt  set_status A1 pass\n")
        _write(td, "book/content/chC.tex", tex)
        fs = cc.check_snippets(
            [("book/content/chC*.tex", "tools/cli.py", "tokens", ("new", "report", "set_status"), None)], td)
        assert fs == [], fs
        fs = cc.check_snippets(
            [("book/content/chC*.tex", "tools/cli.py", "tokens", ("new", "report", "bogus_cmd"), None)], td)
        assert fs and "bogus_cmd" in fs[0].msg, fs


def test_real_mapping_shapes():
    # 真映射表条目形状自检（章 glob / 真源路径 / kind 合法）
    kinds = {"block", "func", "equation", "tokens"}
    assert len(cc.SNIPPETS) >= 12
    assert len(cc.CONSTANTS) >= 12
    for e in cc.SNIPPETS:
        assert e[2] in kinds, e
    for _, _, patterns in cc.CONSTANTS:
        assert patterns


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("PASS", fn.__name__)
    print("consistency_check tests OK (%d)" % len(fns))
