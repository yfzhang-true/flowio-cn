# -*- coding: utf-8 -*-
"""flowio.twin.scenarios — 场景矩阵 (spec §2.7.1 验收语料, 自 electrical_sim 迁入)。

选择独立模块 (而非并入 electrical.py) 的理由:
  * 场景矩阵是**验收/测试资产** —— 12 场景冻结于 docs/mod-baseline/baseline.json
    (对拍基准逐值不可变), 与**物理内核** (ElectricalModel) 生命周期不同:
    新增场景不动模型文件, 模型重构不动语料 (高内聚低耦合的分层点);
  * firmware/twin/electrical_sim.py 薄壳对两者皆 re-export, 消费侧
    (test_electrical_sim.py / tools/compare_baseline.py) 零改动。

兼容: SCENARIOS/run_scenario/run_matrix 与旧 electrical_sim 逐字段同构
(场景定义逐字迁移, 数值锚点不变)。
"""
from flowio.twin.electrical import ElectricalModel

# ---- 场景矩阵 (spec §2.7.1: 至少 单通道充/吸/排/保 + 1-3 通道充气 + 最坏 9 阀 + 搬气 + 过压)
SCENARIOS = {
    "single_inflate": {
        "desc": "单通道充气 (V1+S 保持+泵)", "valves": {"V1": "full_open", "VS": "full_open"},
        "pump": 0.95, "p_m": 0.0},
    "single_vacuum": {
        "desc": "单通道吸气 (V1+V 保持+泵)", "valves": {"V1": "full_open", "VV": "full_open"},
        "pump": 0.95, "p_m": -30.0},
    "single_release": {
        "desc": "单通道排气 (V1+F 保持, 泵停)", "valves": {"V1": "full_open", "VF": "full_open"},
        "pump": 0.0, "p_m": 0.0},
    "single_hold": {
        "desc": "单通道保压 (V1 节能保持)", "valves": {"V1": "economy"},
        "pump": 0.0, "p_m": 25.0},
    "inflate_pull_in_transient": {
        "desc": "充气吸入瞬态 (V1+S 100%≤100ms+泵)", "valves": {"V1": "pull_in", "VS": "pull_in"},
        "pump": 0.95, "p_m": 0.0},
    "inflate_3ch": {
        "desc": "典型 3 通道充气 (V1-3+S 保持+泵)",
        "valves": {"V1": "full_open", "V2": "full_open", "V3": "full_open", "VS": "full_open"},
        "pump": 0.95, "p_m": 0.0},
    "worst_9v_hold_pump": {
        "desc": "最坏 9 阀全开保持+泵95% (受限模式)", "restricted": True,
        "valves": {r: "full_open" for r in
                   ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "VS"]},
        "pump": 0.95, "p_m": 0.0},
    "worst_9v_economy_pump": {
        "desc": "错峰对策: 9 阀节能保持+泵95%",
        "valves": {r: "economy" for r in
                   ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "VS"]},
        "pump": 0.95, "p_m": 0.0},
    "transfer_gas": {
        "desc": "搬气 (S+V+V1 保持+泵, 单泵换向)",
        "valves": {"VS": "full_open", "VV": "full_open", "V1": "full_open"},
        "pump": 0.95, "p_m": 0.0},
    "pump_only_interlock": {
        "desc": "非法工况: 0 通道开起泵 (互锁拦截)",
        "valves": {}, "pump": 0.95, "p_m": 0.0},
    "overpressure": {
        "desc": "过压工况 M=+36kPa (停泵+告警路径)",
        "valves": {"V1": "full_open", "VS": "full_open"}, "pump": 0.95, "p_m": 36.0},
    "vacuum_clamp": {
        "desc": "真空钳位 M=-41kPa (停泵+告警路径)",
        "valves": {"V1": "full_open", "VV": "full_open"}, "pump": 0.95, "p_m": -41.0},
}


def run_scenario(name, params=None):
    """跑单场景 (旧 electrical_sim.run_scenario 同构): 解 + name/desc 标注。"""
    sc = SCENARIOS[name]
    r = ElectricalModel(params).solve(sc["valves"], sc["pump"],
                                      p_manifold_kpa=sc["p_m"])
    r["name"] = name
    r["desc"] = sc["desc"]
    return r


def run_matrix(params=None):
    """场景矩阵全跑 → 摘要行 (name/i/超限/告警/建议/预期)。"""
    rows = []
    for name, sc in SCENARIOS.items():
        r = run_scenario(name, params=params)
        rows.append({
            "name": name, "desc": sc["desc"],
            "i_total_a": r["bus"]["i_total_a"], "over_limit": r["over_limit"],
            "alarms": r["alarms"], "alarm_names": r["alarm_names"],
            "advice": r["advice"],
            "expect_over_limit": bool(sc.get("restricted")),
        })
    return rows


if __name__ == "__main__":                       # 冒烟: 打印矩阵摘要
    for row in run_matrix():
        flag = "OVER" if row["over_limit"] else "ok"
        print("[%-4s] %-28s %8.3f A  %s" % (flag, row["name"],
                                            row["i_total_a"], row["desc"]))
