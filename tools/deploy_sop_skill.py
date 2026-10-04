# -*- coding: utf-8 -*-
"""SOP skill 双源部署：仓库 docs/sop/（源）→ 用户级 skill 目录（部署副本）。
单向同步、幂等。用法: python tools/deploy_sop_skill.py [--check]
  --check 只对比不写（CI 校验用，提示不阻断）。
"""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "docs" / "sop"
DST = Path.home() / ".agents" / "skills" / "flowio-sop"
FILES = ("SKILL.md", "rebuild-matrix.json")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    missing = [f for f in FILES if not (SRC / f).is_file()]
    if missing:
        print(f"FATAL: 源缺失 {missing}")
        return 1

    diffs = []
    for f in FILES:
        s, d = SRC / f, DST / f
        if not d.is_file() or sha(s) != sha(d):
            diffs.append(f)

    if args.check:
        print(f"check: {'IN-SYNC' if not diffs else 'DRIFT ' + diffs}")
        return 0

    if not diffs:
        print(f"IN-SYNC ({DST})")
        return 0

    DST.mkdir(parents=True, exist_ok=True)
    for f in diffs:
        shutil.copyfile(SRC / f, DST / f)
        print(f"deployed: {f} -> {DST / f} ({sha(SRC / f)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
