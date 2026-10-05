# -*- coding: utf-8 -*-
"""flowio.truth.views — pneumatic_devices 条目视图 (冻结 dataclass, M0)。

消费方: electrical_sim.load_params (M0) → ElectricalModel (M2); 结构域
(case_geom 气动塔) M1 迁入。视图 = 值对象: 解析与推导 (r_coil = rated_v /
rated_current_a; drive_policy 百分比/时长字符串) 只此一份 —— 禁止各处手抄
(spec §1 第一原则: 真值到介质的映射必须是生成的, 不是手抄的)。

全部视图函数吃 pneumatic_devices 段 dict (TruthSource.pneumatic_devices
即深拷贝, 可放心消费), 解析失败抛 TruthError (fail-loud)。
"""
import re
from dataclasses import dataclass

from flowio.core.errors import TruthError

_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_MS = re.compile(r"<=?\s*(\d+)\s*ms")


def _pct(s, where):
    m = _PCT.search(str(s))
    if not m:
        raise TruthError("drive_policy %s 无法解析百分比: %r" % (where, s))
    return float(m.group(1)) / 100.0


@dataclass(frozen=True)
class ValveSpec:
    """阀条目 (valves / valve_vacuum_master 两组通用; 差异只在参数)。"""

    refs: tuple                 # 位号组 (如 ("V1",...,"VF"))
    model: str
    group: str                  # valves | valve_vacuum_master
    role: str
    rated_v: float
    rated_current_a: float
    v_range: tuple
    power_w: float
    pressure_kpa: tuple

    @property
    def r_coil(self) -> float:
        """线圈电阻 = rated_v / rated_current_a (electrical 段推导, 唯一出处)。"""
        return self.rated_v / self.rated_current_a


@dataclass(frozen=True)
class PumpSpec:
    """泵条目 (气源, 充吸双口)。"""

    refs: tuple
    model: str
    role: str
    rated_v: float
    load_current_a: float
    v_range: tuple
    power_w: float
    pressure_kpa: tuple
    flow_lpm: float


@dataclass(frozen=True)
class SensorSpec:
    """传感条目 (XGZP6897D 表压, I2C)。"""

    refs: tuple
    model: str
    role: str
    i2c_addr: str
    v_range: tuple
    data_bits: int
    resp_ms: float


@dataclass(frozen=True)
class DrivePolicy:
    """drive_policy 解析视图 (原 electrical_sim._pct/_MS 逻辑收拢于此)。"""

    rail_v: float
    duties: dict                # {pull_in, full_open, economy} → 0~1
    pull_in_ms: float
    pump_max_duty: float
    pump_soft_start: bool


def valve_specs(pn):
    """valves + valve_vacuum_master 两组 → ValveSpec 列表 (每条目一 spec, refs 多值)。"""
    out = []
    for group in ("valves", "valve_vacuum_master"):
        for entry in (pn.get(group) or []):
            try:
                el = entry["electrical"]
                out.append(ValveSpec(
                    refs=tuple(entry["refs"]),
                    model=str(entry.get("model", "")),
                    group=group,
                    role=str(entry.get("role", "")),
                    rated_v=float(el["rated_v"]),
                    rated_current_a=float(el["rated_current_a"]),
                    v_range=tuple(float(x) for x in el["v_range"]),
                    power_w=float(el.get("power_w", 0.0)),
                    pressure_kpa=tuple(float(x) for x in entry.get("pressure_kpa", ())),
                ))
            except (KeyError, TypeError, ValueError) as e:
                raise TruthError("valve 视图解析失败 %s:%s (%s)" % (
                    group, "/".join(entry.get("refs") or ["?"]), e)) from e
    if not out:
        raise TruthError("pneumatic_devices 阀条目缺失 (valves/valve_vacuum_master)")
    return out


def pump_spec(pn):
    """pump 组首条 → PumpSpec。"""
    pumps = pn.get("pump") or []
    if not pumps:
        raise TruthError("pneumatic_devices 泵条目缺失 (pump)")
    entry = pumps[0]
    try:
        el = entry["electrical"]
        return PumpSpec(
            refs=tuple(entry["refs"]),
            model=str(entry.get("model", "")),
            role=str(entry.get("role", "")),
            rated_v=float(el["rated_v"]),
            load_current_a=float(el["load_current_a"]),
            v_range=tuple(float(x) for x in el["v_range"]),
            power_w=float(el.get("power_w", 0.0)),
            pressure_kpa=tuple(float(x) for x in entry.get("pressure_kpa", ())),
            flow_lpm=float(entry.get("flow_lpm", 0.0)),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise TruthError("pump 视图解析失败 P:%s (%s)"
                         % ("/".join(entry.get("refs") or ["?"]), e)) from e


def sensor_spec(pn):
    """sensor 组首条 → SensorSpec。"""
    sensors = pn.get("sensor") or []
    if not sensors:
        raise TruthError("pneumatic_devices 传感条目缺失 (sensor)")
    entry = sensors[0]
    try:
        el = entry["electrical"]
        return SensorSpec(
            refs=tuple(entry["refs"]),
            model=str(entry.get("model", "")),
            role=str(entry.get("role", "")),
            i2c_addr=str(el.get("i2c_addr", "")),
            v_range=tuple(float(x) for x in el["v_range"]),
            data_bits=int(el.get("data_bits", 0)),
            resp_ms=float(el.get("resp_ms", 0.0)),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise TruthError("sensor 视图解析失败 S:%s (%s)"
                         % ("/".join(entry.get("refs") or ["?"]), e)) from e


def drive_policy(pn):
    """_meta.drive_policy → DrivePolicy (百分号/时长字符串解析; 失败 TruthError)。"""
    try:
        dp = pn["_meta"]["drive_policy"]
        m = _MS.search(str(dp["valve"]["pull_in"]))
        if not m:
            raise TruthError("drive_policy pull_in 时长无法解析: %r"
                             % dp["valve"]["pull_in"])
        return DrivePolicy(
            rail_v=float(dp["rail_v"]),
            duties={
                "pull_in": _pct(dp["valve"]["pull_in"], "valve.pull_in"),
                "full_open": _pct(dp["valve"]["full_open_hold"], "valve.full_open_hold"),
                "economy": _pct(dp["valve"]["economy_hold"], "valve.economy_hold"),
            },
            pull_in_ms=float(m.group(1)),
            pump_max_duty=_pct(dp["pump"]["max_duty"], "pump.max_duty"),
            pump_soft_start="互锁" in str(dp["pump"].get("soft_start", "")),
        )
    except TruthError:
        raise
    except (KeyError, TypeError) as e:
        raise TruthError("drive_policy 结构缺失 (%s)" % e) from e
