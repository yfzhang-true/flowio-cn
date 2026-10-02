import board_model as bm
def test_states():
    b=bm.BoardModel(); b.step(0.1,[0]*8,0); s0=b.telemetry()
    assert abs(s0["rail_5v"]["load_a"]-bm.LOGIC_A)<1e-6
    b2=bm.BoardModel(); b2.step(0.005,[1]+[0]*7,0); b2.step(5.0,[1]+[0]*7,0); s1=b2.telemetry()
    assert abs(s1["valves"][0]["i_A"]-5.0/14.04)<0.01
    assert s1["rail_5v"]["load_a"]>5.0/14.04+bm.LOGIC_A-0.02
    b3=bm.BoardModel()
    for _ in range(50): b3.step(0.1,[1]*8,1)
    s8=b3.telemetry()
    assert abs(s8["valves"][7]["i_A"]-5.0/14.04)<0.01 and s8["board_p_w"]>8*1.78
    b4=bm.BoardModel(); b4.step(0.1,[1]+[0]*7,0); b4.step(0.01,[0]*8,0)
    assert 0 <= b4.telemetry()["valves"][0]["i_A"] < 0.35*0.5  # 过零~4.9ms, 10ms时已钳0
    b4.step(0.1,[0]*8,0)
    assert b4.telemetry()["valves"][0]["i_A"] < 0.01
if __name__=="__main__":
    test_states(); print("board_model tests OK")
