# -*- coding: utf-8 -*-
"""FLOWIO-CN P1 嘉立创 PCBA 下单包生成器
从 gen_sch.py 的 PARTS 单一真值源(受限 ast 解释, 禁 exec, 同 gen_pcb.py 模式)提取
ref/value/footprint/LCSC, 生成 JLC 上传格式的 BOM 与 CPL 注释版:
  - fab/flowio-p1-bom-jlc.csv   列: Comment,Designator,Footprint,LCSC Part #
  - fab/flowio-p1-pos-jlc.csv   在 KiCad 导出 pos.csv 前加 # 注释说明(核对法)
用法(任意 python3, 纯 stdlib): python make_bom.py
"""
import ast
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FAB = os.path.join(HERE, "..", "fab")

# ---------------------------------------------------------------- 受限 ast 解释器
# (与 gen_pcb.py 头部同源: 只允许 P() 调用 + 字面量/名/下标/算术/f-string,
#  覆盖 gen_sch.py 里 PARTS 的三种喂料方式: 顶层 += 列表 / for-append / for-+= )
_src = open(os.path.join(HERE, "gen_sch.py"), encoding="utf-8").read()
_tree = ast.parse(_src)

CONSTS = {}
PARTS = []


def _lit(n, env=None):
    env = env or {}
    if isinstance(n, ast.Constant):
        return n.value
    if isinstance(n, ast.Name):
        if n.id in env:
            return env[n.id]
        return CONSTS[n.id]
    if isinstance(n, ast.Subscript):
        return _lit(n.value, env)[_lit(n.slice, env)]
    if isinstance(n, ast.List):
        return [_lit(e, env) for e in n.elts]
    if isinstance(n, ast.Tuple):
        return tuple(_lit(e, env) for e in n.elts)
    if isinstance(n, ast.Dict):
        return {_lit(k, env): _lit(v, env) for k, v in zip(n.keys, n.values)}
    if isinstance(n, ast.BinOp):
        import operator as _op
        _ops = {ast.Add: _op.add, ast.Sub: _op.sub, ast.Mult: _op.mul,
                ast.Div: _op.truediv, ast.FloorDiv: _op.floordiv, ast.Mod: _op.mod}
        if type(n.op) in _ops:
            return _ops[type(n.op)](_lit(n.left, env), _lit(n.right, env))
    if isinstance(n, ast.JoinedStr):
        return "".join(str(_lit(v, env)) for v in n.values)
    if isinstance(n, ast.FormattedValue):
        return _lit(n.value, env)
    raise SystemExit(f"PARTS 依赖不支持的节点: {type(n).__name__} @line {getattr(n, 'lineno', '?')}")


def _iterable(node, env=None):
    env = env or {}
    it = node.iter
    if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
        return range(*[_lit(a, env) for a in it.args])
    if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "enumerate":
        return enumerate(_lit(it.args[0], env))
    return _lit(it, env)


def _pcall(call, env=None):
    env = env or {}
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "P"):
        return None
    names = ["ref", "sym", "val", "fp", "lcsc", "x", "y", "nets"]
    kw = {}
    for i, a in enumerate(call.args):
        kw[names[i]] = _lit(a, env)
    for a in call.keywords:
        kw[a.arg] = _lit(a.value, env)
    return kw


def _collect_partlist(val, env=None):
    env = env or {}
    out = []
    if isinstance(val, (ast.List, ast.Tuple)):
        for e in val.elts:
            d = _pcall(e, env)
            if d:
                out.append(d)
    elif isinstance(val, ast.Call):
        d = _pcall(val, env)
        if d:
            out.append(d)
    return out


def _targets(node):
    return node.targets if isinstance(node, ast.Assign) else [node.target]


for _node in _tree.body:
    if isinstance(_node, (ast.Assign, ast.AugAssign)):
        _t0 = _targets(_node)[0]
        _val = _node.value
        if isinstance(_t0, ast.Name) and _t0.id == "PARTS":
            try:
                PARTS.extend(_collect_partlist(_val))
            except SystemExit:
                raise SystemExit("PARTS 块含不可解析节点 (仅允许 P() 与字面量)")
        elif isinstance(_t0, ast.Tuple):
            for _t, _v in zip(_t0.elts, _val.elts):
                try:
                    CONSTS[_t.id] = _lit(_v)
                except SystemExit:
                    pass
        elif isinstance(_t0, ast.Name):
            try:
                CONSTS[_t0.id] = _lit(_val)
            except SystemExit:
                pass
    elif isinstance(_node, ast.For):
        _touches = any(
            (isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
             and isinstance(s.value.func, ast.Attribute) and s.value.func.attr == "append"
             and isinstance(s.value.func.value, ast.Name) and s.value.func.value.id == "PARTS")
            or (isinstance(s, ast.AugAssign) and isinstance(s.target, ast.Name) and s.target.id == "PARTS")
            for s in _node.body)
        if not _touches:
            continue
        try:
            for _item in _iterable(_node):
                _env = {}
                _tgt = _node.target
                if isinstance(_tgt, ast.Name):
                    _env[_tgt.id] = _item
                elif isinstance(_tgt, (ast.Tuple, ast.List)):
                    for _t, _v in zip(_tgt.elts, _item):
                        _env[_t.id] = _v
                for _stmt in _node.body:
                    if isinstance(_stmt, ast.Expr) and isinstance(_stmt.value, ast.Call):
                        _c = _stmt.value
                        if (isinstance(_c.func, ast.Attribute) and _c.func.attr == "append"
                                and isinstance(_c.func.value, ast.Name) and _c.func.value.id == "PARTS"):
                            _d = _pcall(_c.args[0], _env)
                            if _d:
                                PARTS.append(_d)
                    elif isinstance(_stmt, ast.AugAssign) and isinstance(_stmt.target, ast.Name) \
                            and _stmt.target.id == "PARTS":
                        PARTS.extend(_collect_partlist(_stmt.value, _env))
                    elif isinstance(_stmt, ast.Assign) and isinstance(_stmt.targets[0], ast.Name):
                        _env[_stmt.targets[0].id] = _lit(_stmt.value, _env)
                    elif isinstance(_stmt, ast.AugAssign) and isinstance(_stmt.target, ast.Name):
                        _env[_stmt.target.id] = _env.get(_stmt.target.id, 0) + _lit(_stmt.value, _env) \
                            if isinstance(_stmt.op, ast.Add) else _env[_stmt.target.id]
        except SystemExit as _e:
            raise SystemExit(f"PARTS 循环块不可解析: {_e}")

# ---------------------------------------------------------------- 整理
def ref_key(r):
    m = re.match(r"([A-Z]+)(\d+)", r)
    return (m.group(1), int(m.group(2))) if m else (r, 0)


def is_tht(fp):
    return "CONN-TH" in fp or "DC-IN-TH" in fp


def mpn_of(pt):
    """sym 字段清洗成 MPN: 去掉 JLC 库命名尾缀 _Cxxxxxx / 悬空下划线"""
    s = re.sub(r"_C\d+$", "", pt["sym"] or "")
    return s.rstrip("_")


placed = [p for p in PARTS if p["lcsc"]]                 # 有码 -> 可上贴
noplace = [p for p in PARTS if not p["lcsc"]]            # 无码 (测试点铜皮, 无器件)

# 分组键: (lcsc, footprint, value) — 同码同封装同值合一行
groups = {}
for p in placed:
    key = (p["lcsc"], p["fp"], p["val"])
    groups.setdefault(key, []).append(p["ref"])

rows = []
for (lcsc, fp, val), refs in groups.items():
    refs = sorted(refs, key=ref_key)
    mpn = mpn_of(next(p for p in placed if p["lcsc"] == lcsc and p["fp"] == fp and p["val"] == val))
    rows.append(dict(comment=mpn, refs=refs,
                     fp=fp.split(":", 1)[-1], lcsc=lcsc,
                     tht=is_tht(fp)))
rows.sort(key=lambda r: (r["tht"], ref_key(r["refs"][0])))  # SMT 在前, ref 自然序

smt_rows = [r for r in rows if not r["tht"]]
tht_rows = [r for r in rows if r["tht"]]
n_smt = sum(len(r["refs"]) for r in smt_rows)
n_tht = sum(len(r["refs"]) for r in tht_rows)

# ---------------------------------------------------------------- 写 BOM (JLC 模板 4 列)
bom_path = os.path.join(FAB, "flowio-p1-bom-jlc.csv")
with open(bom_path, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for r in rows:
        w.writerow([r["comment"], ",".join(r["refs"]), r["fp"], r["lcsc"]])

# ---------------------------------------------------------------- 写 CPL 注释版 (pos 原样 + # 说明)
pos_src = os.path.join(FAB, "flowio-p1-pos.csv")
pos_dst = os.path.join(FAB, "flowio-p1-pos-jlc.csv")
_pos = open(pos_src, encoding="utf-8-sig").read().rstrip("\n")
_notes = "\n".join([
    "# FLOWIO-P1 贴片坐标 (JLC CPL 格式: Ref,Val,Package,PosX,PosY,Rot,Side)",
    "#   与 flowio-p1-pos.csv 内容一致; PosY 为负是 KiCad 向下 y 轴导出方向, JLC 直接接受,",
    "#   核对法: 任取 3 行与 fab/assembly-top.pdf 对照 (如 U1 应在板左上、J10-J17 在板底边)。",
    "#   若 JLC 上传器报表头错误: 删除本文件所有 # 行后再传 (原版无注释文件 flowio-p1-pos.csv 仍在)。",
])
with open(pos_dst, "w", encoding="utf-8", newline="") as f:
    f.write(_notes + "\n" + _pos + "\n")

# ---------------------------------------------------------------- 交叉验证
pos_refs = {row["Ref"] for row in csv.DictReader(open(pos_src, encoding="utf-8-sig"))}
bom_refs = {r for row in rows for r in row["refs"]}
only_pos = sorted(pos_refs - bom_refs - {p["ref"] for p in noplace})
only_bom = sorted(bom_refs - pos_refs)

print(f"PARTS 总数: {len(PARTS)}  (可上贴 {len(placed)} / 无码器件 {len(noplace)})")
print(f"BOM 行数:   {len(rows)}  (SMT {len(smt_rows)} 行 {n_smt} 件 / THT {len(tht_rows)} 行 {n_tht} 件)")
print(f"SMT LCSC 码覆盖率: {sum(1 for p in placed if not is_tht(p['fp']))}/{n_smt} = 100%"
      if all(p['lcsc'] for p in placed if not is_tht(p['fp'])) else "SMT 存在缺码!")
print(f"THT LCSC 码覆盖率: {n_tht}/{n_tht} = 100%  "
      f"(J1={rows and next(r['lcsc'] for r in tht_rows if 'DC' in r['fp'])}, "
      f"XH={next(r['lcsc'] for r in tht_rows if '4P-P2.54' in r['fp'])}, "
      f"端子={next(r['lcsc'] for r in tht_rows if 'P5.00' in r['fp'])})")
print(f"无码不上贴: {', '.join(p['ref'] for p in noplace)}  "
      f"(测试点=裸铜焊盘, 无实物件; 安装孔 HA-HD 为板件孔, 均不入 BOM)")
if only_pos:
    print(f"警告: pos 有而 BOM 无: {only_pos}")
if only_bom:
    print(f"警告: BOM 有而 pos 无: {only_bom}")
if not only_pos and not only_bom:
    print(f"交叉验证: BOM {len(bom_refs)} refs == CPL {len(pos_refs)} refs, 一致")
print(f"OK -> {os.path.relpath(bom_path, HERE + '/..')}  {os.path.relpath(pos_dst, HERE + '/..')}")
