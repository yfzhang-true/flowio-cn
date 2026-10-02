#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ticket.py — 验收工单管理器（stdlib，YAML 手写行格式：`key: value` 一行一字段 + `---` 后 Markdown 正文）。

用法（自项目根 E:/FLOWIO/）：
    python book/tools/ticket.py new A205 "WS2812 状态灯" hw 4 [--book-ch 11]
    python book/tools/ticket.py report
    python book/tools/ticket.py set_status A205 pass

工单 = 双产物单元：BRINGUP 勾选 + 书稿素材（spec 2026-10-02-acceptance-book-design.md §1）。
"""
from pathlib import Path
import argparse
import sys

STATUSES = ("pending", "pass", "fail", "waived")
PHASES = ("sw", "hw", "cal")
SEP = "---"
DEFAULT_EVIDENCE = {
    "sw": ["screenshot", "log"],
    "hw": ["photo", "measurement"],
    "cal": ["csv", "plot"],
}


def tickets_dir(root="."):
    return Path(root) / "book" / "tickets"


def _write(path, text):
    Path(path).write_bytes(text.encode("utf-8"))


def _read(path):
    return Path(path).read_bytes().decode("utf-8")


def _fmt_value(v):
    if isinstance(v, list):
        return "[" + ", ".join(str(x) for x in v) + "]"
    return str(v)


def _parse_value(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [x.strip().strip("\"'") for x in inner.split(",") if x.strip()] if inner else []
    return s


def parse(path):
    """解析工单 → (meta dict, body str)。头部为 key: value 行，首个独立 `---` 之后为 Markdown 正文。"""
    text = _read(path)
    lines = text.splitlines()
    meta, body_start = {}, None
    for i, line in enumerate(lines):
        if line.strip() == SEP:
            body_start = i + 1
            break
        if not line.strip() or ":" not in line:
            continue
        key, _, val = line.partition(":")
        meta[key.strip()] = _parse_value(val)
    body = "\n".join(lines[body_start:]).lstrip("\n") if body_start is not None else ""
    return meta, body


def _body(meta, notes=None):
    bid, title = meta["id"], meta["title"]
    phase, bringup, book_ch, status = meta["phase"], meta["bringup"], meta["book_ch"], meta["status"]
    ev = meta.get("evidence_required", [])
    out = []
    out.append(f"# {bid} {title}")
    out.append("")
    out.append(f"- phase: {phase} · BRINGUP §{bringup} · 书稿章 ch{book_ch} · 证据要求: {', '.join(ev)}")
    out.append("")
    out.append("## 操作步骤")
    out.append(f"- [ ] 照 firmware/BRINGUP.md §{bringup} 执行（15-30 分钟工作流，spec §4）")
    out.append("")
    out.append("## 实测值")
    out.append("| 项目 | 期望 | 实测 | 判定 |")
    out.append("|---|---|---|---|")
    out.append("|  |  |  |  |")
    out.append("")
    out.append("## 判定（pass/fail + 容差）")
    out.append(f"- status: {status}" + ("（预填，证据见下）" if status != "pending" else "（待测）"))
    if status == "fail":
        out.append("- fail 同样入书（踩坑实录专栏，spec §1）")
    out.append("")
    if notes:
        out.append("## 证据（已归档）")
        out.extend("- " + n for n in notes)
        out.append("")
    out.append("## 素材管线（产物 → 书稿）")
    out.append("- [ ] 截图/照片拷入 `book/figures/`")
    out.append("- [ ] 数据 CSV 落 `book/data/`")
    out.append(f"- [ ] 书稿 ch{book_ch} 对应节增图/表引用 → xelatex 编译过 → git commit")
    return "\n".join(out) + "\n"


def new(id, title, phase="hw", bringup="", book_ch=11, root=".", status="pending",
        evidence=None, notes=None):
    """生成一张工单模板，落盘 <root>/book/tickets/<id>.yaml，返回元数据 dict。"""
    if phase not in PHASES:
        raise ValueError(f"phase 须为 {PHASES} 之一，得到 {phase!r}")
    if status not in STATUSES:
        raise ValueError(f"status 须为 {STATUSES} 之一，得到 {status!r}")
    meta = {
        "id": id,
        "title": title,
        "phase": phase,
        "bringup": str(bringup) if bringup else "-",
        "book_ch": int(book_ch),
        "status": status,
        "evidence_required": list(evidence) if evidence else list(DEFAULT_EVIDENCE[phase]),
    }
    d = tickets_dir(root)
    d.mkdir(parents=True, exist_ok=True)  # book/tickets/ 目录随首张工单创建
    header = [f"{k}: {_fmt_value(v)}" for k, v in meta.items()]
    text = "\n".join(header) + "\n" + SEP + "\n" + _body(meta, notes)
    _write(d / f"{id}.yaml", text)
    return meta


def report(root="."):
    """扫描 tickets/*.yaml，输出对齐进度表（ID/phase/status/title + 分相汇总）。"""
    d = tickets_dir(root)
    rows = []
    for p in sorted(d.glob("*.yaml")) if d.is_dir() else []:
        meta, _ = parse(p)
        if meta.get("id"):
            rows.append((meta.get("id", p.stem), meta.get("phase", "?"),
                         meta.get("status", "?"), meta.get("title", "")))
    w_id = max([len("ID")] + [len(r[0]) for r in rows] or [2])
    w_ph = max([len("phase")] + [len(r[1]) for r in rows] or [5])
    w_st = max([len("status")] + [len(r[2]) for r in rows] or [6])
    lines = [f"{'ID'.ljust(w_id)}  {'phase'.ljust(w_ph)}  {'status'.ljust(w_st)}  title"]
    lines.append("-" * (w_id + w_ph + w_st + 12))
    lines += [f"{r[0].ljust(w_id)}  {r[1].ljust(w_ph)}  {r[2].ljust(w_st)}  {r[3]}" for r in rows]
    cnt = {s: sum(1 for r in rows if r[2] == s) for s in STATUSES}
    by_phase = {p: sum(1 for r in rows if r[1] == p) for p in PHASES}
    lines.append("-" * (w_id + w_ph + w_st + 12))
    lines.append(f"合计 {len(rows)} 张（sw {by_phase['sw']} / hw {by_phase['hw']} / cal {by_phase['cal']}）："
                 f"pass {cnt['pass']} · pending {cnt['pending']} · fail {cnt['fail']} · waived {cnt['waived']}")
    return "\n".join(lines)


def set_status(id, status, root="."):
    """更新工单 status（保留正文与其余头部字段），返回新元数据。"""
    if status not in STATUSES:
        raise ValueError(f"status 须为 {STATUSES} 之一，得到 {status!r}")
    path = tickets_dir(root) / f"{id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"工单不存在: {path}")
    text = _read(path)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == SEP:
            break
        if line.startswith("status:"):
            lines[i] = f"status: {status}"
    _write(path, "\n".join(lines) + ("\n" if text.endswith("\n") else ""))
    meta, _ = parse(path)
    return meta


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="验收工单管理器（spec 2026-10-02-acceptance-book-design.md）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_new = sub.add_parser("new", help="生成工单模板")
    p_new.add_argument("id")
    p_new.add_argument("title")
    p_new.add_argument("phase", choices=PHASES)
    p_new.add_argument("bringup", help="BRINGUP.md 章节号，如 4 或 9+")
    p_new.add_argument("--book-ch", type=int, default=11)
    p_new.add_argument("--root", default=".")
    p_new.add_argument("--status", default="pending", choices=STATUSES)
    p_new.add_argument("--evidence", help="逗号分隔证据要求，如 photo,serial_log")
    p_new.add_argument("--note", action="append", default=None, help="正文追加一行证据/备注（可多次）")
    p_rep = sub.add_parser("report", help="打印进度表")
    p_rep.add_argument("--root", default=".")
    p_set = sub.add_parser("set_status", help="更新工单状态")
    p_set.add_argument("id")
    p_set.add_argument("status", choices=STATUSES)
    p_set.add_argument("--root", default=".")
    a = ap.parse_args(argv)
    if a.cmd == "new":
        meta = new(a.id, a.title, phase=a.phase, bringup=a.bringup, book_ch=a.book_ch,
                   root=a.root, status=a.status,
                   evidence=[x.strip() for x in a.evidence.split(",")] if a.evidence else None,
                   notes=a.note)
        print(f"新建 {tickets_dir(a.root) / (a.id + '.yaml')} status={meta['status']}")
    elif a.cmd == "report":
        print(report(root=a.root))
    else:
        meta = set_status(a.id, a.status, root=a.root)
        print(f"{a.id} status -> {meta['status']}")


if __name__ == "__main__":
    main()
