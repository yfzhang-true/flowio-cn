# -*- coding: utf-8 -*-
"""python -m flowio — 包执行入口 (M5: 全域子命令 truth|hw|geom|flows|twin|test|rebuild|fwgen)。"""
import sys

from flowio.cli import main

if __name__ == "__main__":
    sys.exit(main())
