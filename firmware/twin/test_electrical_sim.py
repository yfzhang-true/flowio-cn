# -*- coding: utf-8 -*-
"""test_electrical_sim — T7 电气驱动仿真层 TDD 测试 (spec §2.7.1, 无 pytest 用 assert).

红/绿纪律: 本文件先行 (红 = electrical_sim 未实现时 import 即败), 实现后全绿。
运行: cd firmware/twin && python test_electrical_sim.py   (stdlib-only, 任意 python3)

五断言 (spec §2.7.1 验收门槛, 语义按 T7 任务书细化):
  ① 超限检测与告警正确性 —— 正常场景稳态母线电流 ≤ 适配器档 (ADAPTER_A=3.0 初值);
     最坏场景 (9 阀全开保持+泵95% ≈4.12A) 是"受限模式"物理事实 (registry power_budget),
     断言方向 = 仿真层必须检测超限并告警+给错峰建议, 而非"电流必须≤3A";
  ② 稳态执行器有效电压 ∈ [4.05,4.95]V; 节能保持态有意欠压 → 断言 ≥2.5V 且标记
     hold_economy; 吸入瞬态 (≤100ms) 允许 5.0V (drive_policy 吸入 100%);
  ③ 泵占空比 ≤95% (请求超限被钳) + 软启动互锁: 0 通道阀开启时泵必为 0;
  ④ 过压工况 (M>+35kPa 工作带) 停泵+告警路径; 真空钳位 (-40kPa) 同路径;
  ⑤ 参数单源: 临时改 devices.json 阀电流 0.45→0.60 → 仿真输出随之变, 改回即复原
     (finally 保证崩溃也复原, 字节级还原)。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import electrical_sim as es


def _worst_i(params):
    """最坏场景 (9 阀全开保持+泵 95%) 的母线稳态电流, 供⑤前后对比。"""
    r = es.run_scenario("worst_9v_hold_pump", params=params)
    return r["bus"]["i_total_a"]


def test_1_overload_detection():
    """① 超限检测与告警: 正常场景全 ≤3A 且无告警; 最坏场景检测超限+告警+建议。"""
    rows = es.run_matrix()
    assert len(rows) >= 6, f"场景矩阵须≥6, 实得 {len(rows)}"
    normal = [r for r in rows if not r["expect_over_limit"]]
    worst = [r for r in rows if r["expect_over_limit"]]
    assert normal and worst, "矩阵须同时含正常场景与受限模式(预期超限)场景"
    for r in normal:
        assert r["i_total_a"] <= es.ADAPTER_A + 1e-9, \
            f"{r['name']} 稳态母线 {r['i_total_a']:.3f}A > {es.ADAPTER_A}A (应正常或标受限)"
        assert not r["over_limit"], f"{r['name']} 不应告警超限"
    for r in worst:
        assert r["over_limit"], f"{r['name']} 应检测到超限 (受限模式)"
        assert es.ALARM_OVERLOAD in r["alarms"], f"{r['name']} 须带超限告警码"
        assert any("错峰" in a or "节能" in a for a in r["advice"]), \
            f"{r['name']} 须给出错峰/节能保持建议"
    # 物理锚点: 90% 保持时 V_eff=4.5V=额定 → 每阀恰 450mA, 最坏 = 9×0.45+0.5×0.95
    # = 4.525A (registry power_budget "worst=4.55A" 同式同源, 泵取满 0.5);
    # 任务书速算 9×0.45×0.9+0.475≈4.12A 为占空比直折的保守下界 —— 同判 >3A 受限模式
    w = es.run_scenario("worst_9v_hold_pump")
    assert abs(w["bus"]["i_total_a"] - (9 * 0.45 + 0.5 * 0.95)) < 0.01, \
        f"最坏场景锚点 4.525A (registry 4.55A 同源), 实得 {w['bus']['i_total_a']:.3f}A"
    # 受限模式建议本身必须可行: 节能保持 9 阀+泵 = 9×0.275+0.475 = 2.95A ≤ 3A
    eco = es.run_scenario("worst_9v_economy_pump")
    assert not eco["over_limit"] and eco["bus"]["i_total_a"] <= es.ADAPTER_A, \
        "错峰建议 (节能保持) 必须落在适配器档内, 否则建议不可行"


def test_2_steady_voltage_window():
    """② 稳态有效电压 ∈ [4.05,4.95]; 节能保持 ≥2.5 且标记; 吸入瞬态允许 5.0V/≤100ms。"""
    for row in es.run_matrix():
        r = es.run_scenario(row["name"])
        for ref, a in r["actuators"].items():
            if a["state"] == "full_open":                     # 稳态全开保持
                assert 4.05 <= a["eff_v"] <= 4.95, \
                    f"{row['name']}/{ref} 全开保持 eff_v={a['eff_v']:.2f} 出窗 [4.05,4.95]"
                assert not a["hold_economy"]
            elif a["state"] == "economy":                     # 有意欠压保持
                assert a["eff_v"] >= 2.5, \
                    f"{row['name']}/{ref} 节能保持 eff_v={a['eff_v']:.2f} < 2.5V"
                assert a["hold_economy"], "节能保持必须标记 hold_economy (断言豁免依据)"
            elif a["state"] == "pull_in":                     # 瞬态: 100%·5.0V, ≤100ms
                assert a["eff_v"] <= es.load_params()["rail_v"] + 1e-9
                assert a["transient_ms"] <= 100.0, "吸入瞬态必须 ≤100ms (drive_policy)"


def test_3_pump_duty_and_interlock():
    """③ 泵占空比 ≤95% (钳位) + 软启动互锁: 0 通道开启时泵必 0。"""
    p = es.load_params()
    r = es.simulate({ref: "off" for ref in p["valves"]}, 1.0)   # 请求 100%
    assert r["pump"]["duty_eff"] <= 0.95 + 1e-9, "泵占空比须钳至 ≤95% (drive_policy)"
    assert r["pump"]["duty_eff"] == 0.0, "0 通道阀开启 → 泵必 0 (软启动互锁)"
    assert r["pump"]["interlock"], "互锁须置位标记"
    # 合法起泵: 1 通道开 + 主阀开
    v = {ref: "off" for ref in p["valves"]}
    v.update({"V1": "full_open", "VS": "full_open"})
    r2 = es.simulate(v, 1.0)
    assert abs(r2["pump"]["duty_eff"] - 0.95) < 1e-9, "通道开启时泵 100% 请求 → 钳 95%"
    assert not r2["pump"]["interlock"]


def test_4_overpressure_path():
    """④ 过压停泵+告警路径: M>+35 停泵; 真空钳位 -40 同路径。"""
    p = es.load_params()
    v = {ref: "off" for ref in p["valves"]}
    v.update({"V1": "full_open", "VS": "full_open"})
    r = es.simulate(v, 0.95, p_manifold_kpa=35.0)               # 带内临界: 不触发
    assert r["pump"]["duty_eff"] > 0 and not r["alarms"]
    r = es.simulate(v, 0.95, p_manifold_kpa=36.0)               # 越带: 停泵+告警
    assert r["pump"]["duty_eff"] == 0.0, "M>35kPa 必须停泵"
    assert r["pump"]["overpressure_stop"], "须置过压停泵标记"
    assert es.ALARM_OVERPRESSURE in r["alarms"], "须带过压告警码"
    vv = {ref: "off" for ref in p["valves"]}
    vv.update({"V1": "full_open", "VV": "full_open"})
    rv = es.simulate(vv, 0.95, p_manifold_kpa=-41.0)            # 真空钳位
    assert rv["pump"]["duty_eff"] == 0.0 and es.ALARM_VACUUM_CLAMP in rv["alarms"], \
        "M<-40kPa 真空钳位停泵+告警"


def test_5_single_source():
    """⑤ 参数单源: 改 devices.json 阀电流 → 仿真随之变; 字节级复原。"""
    path = es.REGISTRY
    orig = path.read_bytes()
    i0 = _worst_i(None)
    try:
        patched = orig.replace(b'"rated_current_a": 0.45', b'"rated_current_a": 0.60')
        assert patched != orig, "devices.json 中应恰有 F0520D 0.45A 锚串"
        path.write_bytes(patched)
        p2 = es.load_params()                                   # 重新加载 (禁缓存)
        i1 = _worst_i(p2)
        assert abs(i1 - (9 * 0.60 + 0.5 * 0.95)) < 0.01, \
            f"改库后仿真必须跟随 (期望 5.875A, 实得 {i1:.3f}A)"
        assert abs(i1 - i0) > 0.5, "0.45→0.60A 应产生显著电流差"
    finally:
        path.write_bytes(orig)                                  # 崩溃也复原
    assert path.read_bytes() == orig, "devices.json 须字节级复原"
    assert abs(_worst_i(None) - i0) < 1e-9, "复原后仿真回到原值"


def test_6_matrix_smoke():
    """spec §2.7.1 断言⑤原义: 场景矩阵全跑无异常 + 输出契约字段齐备。"""
    for row in es.run_matrix():
        assert {"name", "i_total_a", "over_limit", "alarms", "advice",
                "expect_over_limit"} <= set(row), f"{row.get('name')} 摘要字段缺失"
        r = es.run_scenario(row["name"])
        for key in ("bus", "actuators", "pump", "alarms"):
            assert key in r, f"{row['name']} 缺输出段 {key}"
        for ref, a in r["actuators"].items():
            assert {"state", "duty", "eff_v", "i_a", "p_w",
                    "hold_economy"} <= set(a), f"{row['name']}/{ref} 执行器字段缺失"
    # 全 11 阀在场 (V1-V8/VS/VF/VV) + 泵 —— devices.json pneumatic_devices 单源
    p = es.load_params()
    refs = set(p["valves"])
    assert refs == {"V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "VS", "VF", "VV"}, refs
    assert set(p["duties"]) == {"pull_in", "full_open", "economy"}
    assert abs(p["duties"]["full_open"] - 0.90) < 1e-9 and abs(p["duties"]["economy"] - 0.55) < 1e-9
    assert abs(p["valves"]["VV"]["i_rated"] - 0.30) < 1e-9, "VV=F0520B 0.30A (异于 D 0.45)"


if __name__ == "__main__":
    test_1_overload_detection()
    test_2_steady_voltage_window()
    test_3_pump_duty_and_interlock()
    test_4_overpressure_path()
    test_5_single_source()
    test_6_matrix_smoke()
    print("electrical_sim tests OK (6 testfns / 5 assertions + smoke)")
