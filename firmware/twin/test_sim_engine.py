# -*- coding: utf-8 -*-
"""test_sim_engine — S1 参数化仿真引擎 TDD 测试 (KiCad Python 无 pytest, 用 assert).
运行: cd firmware/twin && "E:/Program Files/KiCad/10.0/bin/python.exe" test_sim_engine.py
锚点: buck Vout=3.269V / 纹波<50mV@3A; valve 拉入≈0.498A (r_coil=10Ω, registry); i2c tr=2.2·RC."""
import sim_engine as se


def test_buck_default_anchor():
    r = se.run("buck", {})
    m = {x["name"]: x["value"] for x in r["metrics"]}
    assert abs(m["输出电压"] - 3.269) < 0.01
    assert m["稳态纹波"] < 50 and "waves" in r and len(r["waves"]) >= 2


def test_param_bounds():
    for bad in [{"vin": 6.0}, {"vin": 3.0}, {"iload": 3.5}, {"fsw_khz": 200}]:
        try:
            se.run("buck", bad); assert False, bad
        except se.ParamError:
            pass


def test_dior_valve_i2c_smoke():
    assert se.run("dior", {})["metrics"]
    r = se.run("valve", {"pwm_hz": 20}); assert abs(r["metrics"][0]["value"] - 0.498) < 0.02  # r_coil=10Ω (registry)
    r = se.run("i2c", {"rp_k": 2.2}); assert r["metrics"][0]["value"] < 2e-6
    # tr 精确锚点 (µs): 2.2·RC = 2.2×2.2k×115pF = 0.557µs; value 为 SI 秒, ×1e6 换算后比较
    assert abs(r["metrics"][0]["value"] * 1e6 - 2.2 * 2.2e3 * 115e-12 * 1e6) < 0.05


if __name__ == "__main__":
    test_buck_default_anchor(); test_param_bounds(); test_dior_valve_i2c_smoke()
    print("sim_engine tests OK")
