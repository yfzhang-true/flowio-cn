// firmware/twin/webapp/js/flows.js — 电流辉光 + 气流粒子 (数据驱动, 长在产品上)
// 电流: Line+ShaderMaterial 行进虚线; 气流: Points 沿 QuadraticBezier (flows.json 3 控制点);
// 爆炸跟随: 流组每帧复制 pcb 部件位移 (端点绑定), 呼吸由父 asm 组携带 → 连线不断。
// M4: three 解析改走 importmap 裸说明符 "three" (与 scene.js/vendor addons 同源)。
import * as THREE from "three";

const LINE_VS = `attribute float aT; varying float vT; void main(){ vT=aT;
  gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }`;
const LINE_FS = `uniform float uTime,uSpeed,uGain; uniform vec3 uColor; varying float vT;
  void main(){ float d = fract(vT*40. - uTime*uSpeed); float dash = smoothstep(.0,.15,d)*smoothstep(.5,.35,d);
  float a = (0.08 + dash*0.92) * uGain; gl_FragColor = vec4(uColor, a); }`;

const AIR_P = 0x6ad4ff, AIR_V = 0xffb454;        // 正压青 / 真空琥珀
const N_PART = 50;                                // 每端口粒子数 (总量 8×50=400 ≤ 预算 500)
const clamp01 = (v) => Math.min(1, Math.max(0, v));
const frac = (x) => ((x % 1) + 1) % 1;

function dotTexture() {                           // 圆点粒子贴图
  const c = document.createElement("canvas");
  c.width = c.height = 32;
  const g = c.getContext("2d");
  const rg = g.createRadialGradient(16, 16, 1, 16, 16, 15);
  rg.addColorStop(0, "rgba(255,255,255,1)");
  rg.addColorStop(0.4, "rgba(255,255,255,.85)");
  rg.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = rg;
  g.fillRect(0, 0, 32, 32);
  return new THREE.CanvasTexture(c);
}

// live 字段 → 归一激励 (valves[n].i_A/0.36, load_a/3.0)
function live01For(live, tel) {
  if (!tel || !live) return 0;
  const m = /^valves\[(\d+)\]\.i_A$/.exec(live);
  if (m) { const v = tel.valves && tel.valves[+m[1]]; return v ? clamp01((v.i_A || 0) / 0.36) : 0; }
  if (live === "rail_5v.load_a") return clamp01(((tel.rail_5v || {}).load_a || 0) / 3.0);
  if (live === "rail_3v3.load_a") return clamp01(((tel.rail_3v3 || {}).load_a || 0) / 3.0);
  return 0;
}

// QuadraticBezier 求值 (标量存形避免 Vector3 分配)
function qbInto(out, o, P0, P1, P2, t) {
  const u = 1 - t, a = u * u, b = 2 * u * t, c = t * t;
  out[o] = a * P0[0] + b * P1[0] + c * P2[0];
  out[o + 1] = a * P0[1] + b * P1[1] + c * P2[1];
  out[o + 2] = a * P0[2] + b * P1[2] + c * P2[2];
}

export async function createFlows(parent, opts = {}) {
  const data = await (await fetch("/webapp/flows.json")).json();
  const getPcb = opts.getPcb || (() => null);
  const group = new THREE.Group();
  parent.add(group);

  // ── 电流: 每路径一条行进虚线 (aT=弧长归一) ─────────────────────
  const lines = {};
  for (const p of data.elec || []) {
    const pts = p.points.map((a) => new THREE.Vector3(a[0], a[1], a[2] + 0.35)); // 微悬于板面防 z-fight
    const cum = [0];
    for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + pts[i].distanceTo(pts[i - 1]));
    const total = cum[cum.length - 1] || 1;
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    geo.setAttribute("aT", new THREE.BufferAttribute(new Float32Array(pts.map((_, i) => cum[i] / total)), 1));
    const uniforms = {
      uTime: { value: 0 }, uSpeed: { value: 0.6 }, uGain: { value: 0.25 },
      uColor: { value: new THREE.Color(p.color) },
    };
    const mesh = new THREE.Line(geo, new THREE.ShaderMaterial({
      vertexShader: LINE_VS, fragmentShader: LINE_FS, uniforms,
      transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    group.add(mesh);
    lines[p.id] = { id: p.id, mesh, uniforms, live: p.live, desc: p.desc, live01: 0 };
  }

  // ── 气流: 每端口 8% 底光线 + 50 粒沿 Bezier 循环 ──────────────
  // depthTest:false + 高 renderOrder: 开孔在 +Y 侧壁, 默认视角下管路被壳/端子体遮挡,
  // 叠加式辉光让"通道存在/气流喷出"始终可见 (spec §3.2 底光语义); 电流线保持深度遮挡。
  const tex = dotTexture();
  const airs = [];
  for (const a of data.air || []) {
    const P0 = a.start, P1 = a.ctrl, P2 = a.end;
    const cpts = [];
    for (let i = 0; i <= 24; i++) { const v = [0, 0, 0]; qbInto(v, 0, P0, P1, P2, i / 24); cpts.push(new THREE.Vector3(v[0], v[1], v[2])); }
    const base = new THREE.Line(new THREE.BufferGeometry().setFromPoints(cpts),
      new THREE.LineBasicMaterial({ color: AIR_P, transparent: true, opacity: 0.1, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false }));
    base.renderOrder = 10;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(N_PART * 3), 3).setUsage(THREE.DynamicDrawUsage));
    const mat = new THREE.PointsMaterial({
      size: 1.8, map: tex, transparent: true, opacity: 0, depthWrite: false, depthTest: false,
      blending: THREE.AdditiveBlending, color: AIR_P,
    });
    const points = new THREE.Points(geo, mat);
    points.frustumCulled = false;
    points.renderOrder = 11;
    group.add(base, points);
    const phase = new Float32Array(N_PART);
    for (let i = 0; i < N_PART; i++) phase[i] = frac(i / N_PART + (Math.random() - 0.5) * 0.012);
    airs.push({ id: a.id, ref: a.ref, P0, P1, P2, base, points, mat, phase, duty01: 0, dir: 1, op: 0 });
  }

  const st = { tel: null, pnu: null, connected: false, pressureSign: 1 };

  // 数据入口: {tel(board/state), pnu(/api/state), connected} → 目标参数
  function update(d = {}) {
    if ("tel" in d) st.tel = d.tel;
    if ("pnu" in d) st.pnu = d.pnu;
    if ("connected" in d) st.connected = d.connected;
    const pp = ((st.pnu && st.pnu.ports_p) || []).find((v) => Math.abs(v) > 0.05);
    if (pp !== undefined) st.pressureSign = pp < 0 ? -1 : 1;
    for (const id in lines) lines[id].live01 = st.connected ? live01For(lines[id].live, st.tel) : 0;
    for (const a of airs) {
      const n = parseInt(a.id.slice(4), 10) - 1;
      let duty = 0;
      if (st.connected) {
        const v = st.pnu && Array.isArray(st.pnu.valves) ? st.pnu.valves[n] : undefined;
        duty = v !== undefined ? v / 255
          : (st.tel && st.tel.valves && st.tel.valves[n] && st.tel.valves[n].on ? 1 : 0);
      }
      a.duty01 = clamp01(duty);
      a.dir = st.pressureSign < 0 ? -1 : 1;
    }
  }

  // 每帧: uniforms/粒子直写 + 增益平滑 (断连→底光 0.08, 粒子淡出)
  function tick(t, dt) {
    const pcb = getPcb();
    if (pcb) group.position.copy(pcb.position);   // 爆炸跟随 (pcb 部件位移)
    for (const id in lines) {
      const L = lines[id];
      const gain = st.connected ? 0.25 + 0.75 * L.live01 : 0.08;
      L.uniforms.uGain.value += (gain - L.uniforms.uGain.value) * Math.min(1, dt * 6);
      L.uniforms.uTime.value = t;
      L.uniforms.uSpeed.value = 0.6 + 2.2 * L.live01;
    }
    for (const a of airs) {
      const opT = st.connected && a.duty01 > 0.01 ? 0.3 + 0.7 * a.duty01 : 0;
      a.op += (opT - a.op) * Math.min(1, dt * 5);
      a.mat.opacity = a.op;
      const col = a.dir < 0 ? AIR_V : AIR_P;
      a.mat.color.setHex(col);
      a.base.material.color.setHex(col);
      a.base.material.opacity = st.connected ? 0.1 : 0.03;
      const speed = (0.15 + 0.85 * a.duty01) * a.dir;   // 真空=方向反转 (t 递减)
      const pos = a.points.geometry.attributes.position.array;
      for (let i = 0; i < N_PART; i++) {
        a.phase[i] = frac(a.phase[i] + speed * dt);
        qbInto(pos, i * 3, a.P0, a.P1, a.P2, a.phase[i]);
      }
      a.points.geometry.attributes.position.needsUpdate = true;
    }
  }
  update({});

  const handle = { group, lines, airs, update, tick, state: st };
  window.__t2 = window.__t2 || {};
  window.__t2.flows = handle;                     // T7 测试调试钩
  return handle;
}
