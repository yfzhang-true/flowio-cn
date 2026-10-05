# -*- coding: utf-8 -*-
"""flowio.cli — 包级命令行入口 (M3 最小版: 仅 fwgen; M5 扩全域子命令)。

入口选择 (任务裁定说明): 采用包内 `python -m flowio fwgen`, 不另设
tools/gen_params.py 独立脚本 —— spec §2 包结构即 cli.py 单入口, M5 追加
truth|hw|geom|flows|twin|webgen 子命令时零迁移; tools/ 只留对拍器
(compare_baseline.py) 与 CI 门 (check_codegen.py), 避免双入口漂移。
"""
from __future__ import annotations

import argparse
import sys

from flowio import fwgen
from flowio.core.truth import TruthSource


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m flowio",
        description="FLOWIO-CN 数字孪生内核 CLI (M3 最小版: fwgen 三语参数生成)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    fw = sub.add_parser(
        "fwgen", help="固件/前端参数生成 (M3): types.h (D1=B) + params_gen.js")
    fw.add_argument("--truth", default=None, metavar="PATH",
                    help="devices.json 路径 (默认仓库真值, FLOWIO_TRUTH 可覆盖)")
    fw.add_argument("--check", action="store_true",
                    help="只校验不写盘: 重渲染与库内全等 rc=0, 漂移 rc=1")
    fw.add_argument("--out-root", default=None, metavar="DIR",
                    help="输出根目录 (默认仓库根; 预览/测试用)")

    args = ap.parse_args(argv)
    truth = TruthSource(args.truth)

    if args.cmd == "fwgen":
        if args.check:
            sync = fwgen.check_artifacts(args.out_root, truth)
            for rel, ok in sorted(sync.items()):
                print("[%s] %s" % ("OK  " if ok else "DRIFT", rel))
            drifted = [r for r, ok in sorted(sync.items()) if not ok]
            if drifted:
                print("fwgen --check: %d 生成物漂移 → 重生成: python -m flowio fwgen"
                      % len(drifted))
                return 1
            print("fwgen --check: %d/%d 生成物与真值渲染全等" % (len(sync), len(sync)))
            return 0
        for p in fwgen.write_all(truth, args.out_root):
            print("written %s" % p)
        return 0
    ap.error("未知子命令: %s" % args.cmd)          # pragma: no cover (argparse 兜底)
    return 2


if __name__ == "__main__":
    sys.exit(main())
