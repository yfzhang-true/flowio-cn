// firmware/twin/webapp/js/params_gen.js — 三语参数生成物 · TS/ES module 侧 (M3, spec v2.1 §3.5)
// ⚠ 生成文件 (DO NOT EDIT): `python -m flowio fwgen` ← hardware/flowio-p1/enclosure/devices.json
//   手改必被 tools/check_codegen.py --ci 打红; 改参数 = 改真值后重生成。
//   同源生成: firmware/components/pn_core/include/pn_core/types.h (C 侧, D1=B)。
// 语义: 真值只读快照 + 少量推导 (hold_duty_255 = 255×full_open_hold 四舍五入,
//   与 C 侧 PN_HOLD_DEFAULT_DUTY 同推导同值 —— 三方对拍锚点)。
// 注: 泵正压死头 twin 仿真取 61 (twin_api.c 本地策略值, FlowIO Small 实测),
//   非 registry 死头能力 120 (p_max_kpa) —— 双值并存属设计, 见 PHYSICS-SPEC。
export const FLOWIO_PARAMS = Object.freeze({
  rail_v: 5.0,  // [registry] pneumatic_devices._meta.drive_policy.rail_v
  valve: Object.freeze({
    hold_duty_255: 230,  // [registry] pneumatic_devices._meta.drive_policy.valve.full_open_hold 百分比 → 255 制字节 (与 C 侧 PN_HOLD_DEFAULT_DUTY 同推导)
    hold_delay_ms: 100,  // [registry] pneumatic_devices._meta.drive_policy.valve.pull_in 吸入窗
    pull_in_duty: 1.0, economy_duty: 0.55,  // [registry] pull_in/economy_hold
    full_open_duty: 0.9,  // [registry] full_open_hold (hold_duty_255 的百分比源)
    min_actuation_v: 4.1,  // [registry] pneumatic_devices._meta.drive_policy.voltage_adequacy.min_actuation_v (最低动作电压)
    rated_v: 4.5, rated_current_a: 0.45, pressure_kpa: Object.freeze([0.0, 45.0]),  // [registry] valves[0] F0520D-DC4.5V
  }),
  pump: Object.freeze({
    max_duty: 0.95,  // [registry] pneumatic_devices._meta.drive_policy.pump.max_duty
    p_min_kpa: -60.0, p_max_kpa: 120.0,  // [registry] pump[0].pressure_kpa (死头能力; 孪生仿真死点另见 twin_api.c 注与本文件 banner)
    rated_v: 4.5, load_current_a: 0.5, flow_lpm: 2.8,  // [registry] pump[0] ZR370-03PM-DC4.5V
  }),
  sensor: Object.freeze({
    i2c_addr: "0x6D", v_range: Object.freeze([2.5, 5.5])  // [registry] sensor[0] XGZP6897D 100KPDPN（非-C）
  }),
});
