# -*- coding: utf-8 -*-
"""flowio.core.truth — TruthSource: devices.json 单一真值封装 (spec v2.1 §3.3)。

封装纪律:
  * 私有 _load/_validate, 公共只读属性 (devices/pneumatic_devices/path) ——
    属性赋值必抛 AttributeError, 返回值深拷贝 (改返回结构不污染源快照);
  * 加载/校验失败抛 TruthError = FAIL (fail-loud, 禁静默兜底);
  * 实例 = 一次快照 (惰性加载后缓存于实例); 「每次全量读盘」语义由调用方
    每次 new TruthSource 实现 (electrical_sim.load_params 即此用法 —— 断言⑤
    '改库即改仿真' 依赖无缓存)。

路径解析 (优先级):
  1. 构造参数 path;
  2. 环境变量 FLOWIO_TRUTH (测试/多环境真值切换);
  3. 默认 <仓库根>/hardware/flowio-p1/enclosure/devices.json
     (仓库根 = 本文件 parents[2], 即 flowio 包的上级目录)。

校验器: flowio.truth.predicates.document_problems —— 真值域 schema 谓词聚合,
懒导入以避免 core→truth 包级硬依赖 (core 保持零域知识可独立 import)。
"""
import copy
import json
import os
from pathlib import Path

from flowio.core.errors import TruthError

_DEFAULT_TRUTH = (Path(__file__).resolve().parents[2] / "hardware" / "flowio-p1"
                  / "enclosure" / "devices.json")


def default_truth_path() -> Path:
    """默认真值路径 (FLOWIO_TRUTH 环境变量优先于仓库根默认)。"""
    env = os.environ.get("FLOWIO_TRUTH")
    return Path(env) if env else _DEFAULT_TRUTH


class TruthSource:
    """devices.json 只读视图源 (两段: devices / pneumatic_devices)。"""

    def __init__(self, path=None):
        self._path = Path(path) if path is not None else default_truth_path()
        self._doc = None                       # 惰性加载的快照 (实例内缓存)

    # ---- 私有: 载载 + 校验 -------------------------------------------------
    def _load(self) -> dict:
        try:
            with self._path.open(encoding="utf-8") as f:
                doc = json.load(f)
        except OSError as e:
            raise TruthError("真值文件不可读: %s (%s)" % (self._path, e)) from e
        except json.JSONDecodeError as e:
            raise TruthError("真值文件非合法 JSON: %s (%s)" % (self._path, e)) from e
        if not isinstance(doc, dict):
            raise TruthError("真值根必须是 JSON 对象: %s" % self._path)
        return doc

    def _validate(self, doc: dict) -> None:
        from flowio.truth.predicates import document_problems   # 懒导入 (见模块注释)
        problems = document_problems(doc)
        if problems:
            raise TruthError("真值 schema 校验失败: %s | %s"
                             % (self._path, "; ".join(problems[:6])))

    def _ensure(self) -> None:
        if self._doc is None:
            doc = self._load()
            self._validate(doc)
            self._doc = doc

    # ---- 公共: 只读属性 ------------------------------------------------------
    @property
    def path(self) -> Path:
        """真值文件路径 (只读)。"""
        return self._path

    @property
    def devices(self) -> list:
        """devices 段 (PCB 贴装器件条目列表; 深拷贝, 只读快照)。"""
        self._ensure()
        return copy.deepcopy(self._doc["devices"])

    @property
    def pneumatic_devices(self) -> dict:
        """pneumatic_devices 段 (气动器件: valves/valve_vacuum_master/pump/sensor)。"""
        self._ensure()
        return copy.deepcopy(self._doc["pneumatic_devices"])

    def __repr__(self) -> str:
        return "TruthSource(%s%s)" % (self._path, " [loaded]" if self._doc is not None else "")
