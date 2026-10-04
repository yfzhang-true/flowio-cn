import board_model as bm
def test_states():
    b=bm.BoardModel(); b.step(0.1,[0]*8,0); s0=b.telemetry()
    assert abs(s0["rail_5v"]["load_a"]-bm.LOGIC_A)<1e-6
    b2=bm.BoardModel(); b2.step(0.005,[1]+[0]*7,0); b2.step(5.0,[1]+[0]*7,0); s1=b2.telemetry()
    assert abs(s1["valves"][0]["i_A"]-5.0/10.04)<0.01   # r_coil=10Ω (registry 4.5V/0.45A) + rds
    assert s1["rail_5v"]["load_a"]>5.0/10.04+bm.LOGIC_A-0.02
    b3=bm.BoardModel()
    for _ in range(50): b3.step(0.1,[1]*8,1)
    s8=b3.telemetry()
    assert abs(s8["valves"][7]["i_A"]-5.0/10.04)<0.01 and s8["board_p_w"]>8*2.2  # ≈0.5A/阀
    b4=bm.BoardModel(); b4.step(0.1,[1]+[0]*7,0); b4.step(0.01,[0]*8,0)
    assert 0 <= b4.telemetry()["valves"][0]["i_A"] < 0.50*0.5  # 过零~6.9ms(tau 2.5ms), 10ms时已钳0
    b4.step(0.1,[0]*8,0)
    assert b4.telemetry()["valves"][0]["i_A"] < 0.01
def test_buck_losses():
    # loss_mw 随负载动态 (v5 跌 → D 升): 不再是 @3A 常量快照, 断言量级 + 动态性
    b=bm.BoardModel(); b.step(0.1,[0]*8,0); s0=b.telemetry(); l0=s0["rail_3v3"]["loss_mw"]
    assert all(0<v<2000 for v in l0.values()) and sum(l0.values())>0
    assert 0<s0["rail_3v3"]["buck_eff"]<1
    for _ in range(50): b.step(0.1,[1]*8,1)       # 满载 → v5 跌 → 损耗随之变化
    l8=b.telemetry()["rail_3v3"]["loss_mw"]
    assert all(0<v<2000 for v in l8.values()) and sum(l8.values())>0 and l8!=l0
if __name__=="__main__":
    test_states(); test_buck_losses(); print("board_model tests OK")
