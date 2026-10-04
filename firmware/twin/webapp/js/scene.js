// firmware/twin/webapp/js/scene.js — 全屏产品场景: 装配叙事 / 爆炸 / Liquid Glass 材质 / 热点
// 坐标系 = 壳系 Z-up (与 meshes/*.stl、flows.json 同源, 无任何翻转);
// 爆炸语义同 S3: part.position = explode * k; 装配叙事初始 k=1 且额外位移 ×2.5 (即 ×3) 1.5s easeOutQuint 归零。
import * as THREE from "/webapp/vendor/three.module.js";
import { OrbitControls } from "/webapp/vendor/addons/OrbitControls.js";
import { STLLoader } from "/webapp/vendor/addons/STLLoader.js";
import { RoomEnvironment } from "/webapp/vendor/addons/RoomEnvironment.js";

const easeOutQuint = (t) => 1 - Math.pow(1 - t, 5);

// 材质表 (plan Task3: 器件中性灰 / PCB 墨绿微金属 / 壳喷砂灰)
const PART_MATS = {
  parts_F:     { color: 0xb9bcc2, roughness: 0.50, metalness: 0.10, env: 0.85 },
  pcb:         { color: 0x0f3d2a, roughness: 0.65, metalness: 0.25, env: 0.75 },
  case_top:    { color: 0x9a9a9e, roughness: 0.55, metalness: 0.20, env: 0.90 },
  case_bottom: { color: 0x8f8f93, roughness: 0.55, metalness: 0.20, env: 0.80 },
};

function makeGroundShadowTex() {
  // ContactShadow 替代 (r16x 无内建): 径向透明渐变 CanvasTexture 贴地
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const g = c.getContext("2d");
  const rg = g.createRadialGradient(128, 128, 8, 128, 128, 126);
  rg.addColorStop(0.0, "rgba(0,0,0,0.50)");
  rg.addColorStop(0.55, "rgba(0,0,0,0.22)");
  rg.addColorStop(1.0, "rgba(0,0,0,0)");
  g.fillStyle = rg;
  g.fillRect(0, 0, 256, 256);
  return new THREE.CanvasTexture(c);
}

export async function createScene(canvas, onPartClick = () => {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setClearColor(0x000000, 0);           // 透出 CSS 径向渐变画布底 (spec §4)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(renderer), 0.04).texture;

  const camera = new THREE.PerspectiveCamera(38, 2, 0.1, 500);
  camera.up.set(0, 0, 1);                       // 壳系 Z-up
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.maxPolarAngle = 1.45;                // 不钻到地面影之下

  // 顶亮 / 底暗双平行光 + 环境反射
  const key = new THREE.DirectionalLight(0xffffff, 1.7);
  key.position.set(60, -70, 180);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x8fb2ff, 0.55);
  fill.position.set(-90, 80, -50);
  scene.add(fill);

  // 整机组: 呼吸悬浮作用域 (部件 + 流线都挂这里)
  const asm = new THREE.Group();
  scene.add(asm);

  // 地面渐变圆盘 (ContactShadow 替代): 半径 62mm, 贴地 z=-20, 爆炸时微随下沉
  const shadow = new THREE.Mesh(
    new THREE.CircleGeometry(62, 48),
    new THREE.MeshBasicMaterial({ map: makeGroundShadowTex(), transparent: true, depthWrite: false })
  );
  shadow.position.z = -20;
  shadow.renderOrder = -1;
  scene.add(shadow);

  // ── STL 装配 (assembly.json 同源) ──────────────────────────────
  const man = await (await fetch("/api/board/assembly")).json();
  if (!man || !Array.isArray(man.parts) || !man.parts.length) throw new Error("装配清单为空");
  const bb = man.bbox_mm || [202.7, 85.8, 57.0];  // case_geom.BBOX_MM 同源 (P1.1 T6 双体: 主模块+气动塔+泵模块)
  const center = new THREE.Vector3(bb[0] / 2, bb[1] / 2, bb[2] / 2);

  const loader = new STLLoader();
  const parts = [];
  const meshes = await Promise.all(man.parts.map(async (part) => {   // 并行加载缩短首帧
    const buf = await (await fetch(part.stl)).arrayBuffer();
    const geo = loader.parse(buf);
    geo.computeVertexNormals();                 // 非索引几何 → 平面法线 (CAD 质感)
    const m = PART_MATS[part.id] || { color: 0x9a9a9e, roughness: 0.55, metalness: 0.2, env: 0.8 };
    const mat = new THREE.MeshStandardMaterial({
      color: m.color, roughness: m.roughness, metalness: m.metalness,
      envMapIntensity: m.env, emissive: new THREE.Color(0x6aa9ff), emissiveIntensity: 0,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.userData = { partId: part.id, name: part.name || part.id };
    const ex = part.explode || [0, 0, 0];
    mesh.position.set(ex[0] * 3, ex[1] * 3, ex[2] * 3);   // 初始散位 = explode ×3 (intro 起点)
    asm.add(mesh);
    return { id: part.id, name: part.name || part.id, mesh, explode: new THREE.Vector3(ex[0], ex[1], ex[2]) };
  }));
  parts.push(...meshes);

  camera.position.set(center.x + 26, center.y - 148, center.z + 62);
  controls.target.set(center.x, center.y + 10, 2);
  controls.minDistance = 40;
  controls.maxDistance = 420;
  controls.update();

  // ── 器件热点 (hotspots.json: ref→{center,size}) ────────────────
  const hsData = await (await fetch("/webapp/hotspots.json")).json();
  const hotspots = [];
  const pickables = [];
  for (const h of hsData.hotspots || []) {
    const size = new THREE.Vector3(
      Math.max(h.size[0], 2.5), Math.max(h.size[1], 2.5), Math.max(h.size[2], 2.0));
    const box = new THREE.Mesh(
      new THREE.BoxGeometry(size.x * 1.15, size.y * 1.15, size.z * 1.15),
      new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }));
    box.position.set(h.center[0], h.center[1], h.center[2]);
    box.userData = { hotspot: h };
    asm.add(box);
    hotspots.push({ ref: h.ref, name: h.name, live: h.live, box, center: h.center, size: h.size });
    pickables.push(box);
  }
  for (const p of parts) pickables.push(p.mesh);   // 部件级兜底拾取

  // hover 发光框 (Apple 产品页 hotspot 语义)
  const hoverBox = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(1, 1, 1)),
    new THREE.LineBasicMaterial({ color: 0x6aa9ff, transparent: true, opacity: 0.9 }));
  hoverBox.visible = false;
  asm.add(hoverBox);

  // ── 拾取 (raycaster: 器件优先, 空白→null 关卡) ─────────────────
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  const pulses = new Map();                       // partId → t0 (pulsePart)
  let highlightId = null;

  function pick(ev) {
    const r = canvas.getBoundingClientRect();
    ndc.x = ((ev.clientX - r.left) / r.width) * 2 - 1;
    ndc.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
    ray.setFromCamera(ndc, camera);
    const hits = ray.intersectObjects(pickables, false);
    const hsHit = hits.find((x) => x.object.userData.hotspot);   // 器件级优先于部件级
    if (hsHit) {
      const hs = hsHit.object.userData.hotspot;
      return { type: "hotspot", ref: hs.ref, name: hs.name, live: hs.live, center: hs.center, size: hs.size };
    }
    const pt = hits.find((x) => x.object.userData.partId);
    return pt ? { type: "part", partId: pt.object.userData.partId, name: pt.object.userData.name } : null;
  }
  canvas.addEventListener("pointerdown", (ev) => onPartClick(pick(ev)));
  canvas.addEventListener("pointermove", (ev) => {
    const h = pick(ev);
    canvas.style.cursor = h ? "pointer" : "";
    if (h && h.type === "hotspot") {
      hoverBox.visible = true;
      hoverBox.scale.set(h.size[0] * 1.15, h.size[1] * 1.15, h.size[2] * 1.15);
      hoverBox.position.set(h.center[0], h.center[1], h.center[2]);
    } else hoverBox.visible = false;
  });
  canvas.addEventListener("pointerleave", () => { hoverBox.visible = false; });

  // ── 动画状态: 装配叙事 + 爆炸缓动 + 呼吸 ───────────────────────
  let kTarget = 0;                                // 滑杆目标
  let kCur = 0;                                   // 平滑值
  let introT0 = -1;                               // 渲染循环启动时才起表 (flows 加载不占叙事窗口)
  let lastT = 0;
  const INTRO = 1.5;
  let flowsTick = null;                           // Task4: flows 渲染回调
  let fps = 0;

  function setExplode(k) {
    kTarget = Math.min(1, Math.max(0, +k || 0));
    return kTarget;
  }
  function setHighlight(partId) {
    highlightId = partId || null;
    for (const p of parts)                              // 立即生效 (渲染帧同步重算)
      p.mesh.material.emissiveIntensity = p.id === highlightId ? 0.35 : 0;
    return highlightId;
  }
  function pulsePart(partId) {
    if (parts.some((p) => p.id === partId)) { pulses.set(partId, lastT); return true; }
    return false;
  }

  function render(t) {
    if (introT0 < 0) { introT0 = t + 0.12; lastT = t; }   // 首帧起表
    const dt = Math.min(0.1, Math.max(0, t - lastT));
    lastT = t;
    if (dt > 0) fps = fps ? fps * 0.92 + (1 / dt) * 0.08 : 1 / dt;

    // 装配叙事: m 从 3 (k=1 全爆+×2.5) easeOutQuint 收敛到 kTarget; 之后 kCur 指数缓动跟随滑杆
    let m;
    const it = (t - introT0) / INTRO;
    if (it < 1) {
      m = 3 + (kTarget - 3) * easeOutQuint(Math.max(0, it));
      kCur = kTarget * (1 - Math.max(0, it));    // 同步 kCur 供影碟/流跟随
    } else {
      kCur += (kTarget - kCur) * (1 - Math.exp(-dt * 12));   // 帧率无关缓动
      m = kCur;
    }
    for (const p of parts) p.mesh.position.copy(p.explode).multiplyScalar(m);

    asm.position.z = Math.sin(t / 4) * 0.3;       // 呼吸悬浮 (整机组 0.3mm)
    shadow.position.z = -20 - kCur * 14;          // 爆炸时影碟微随下沉

    // 高亮 / 脉冲 emissive (spec §3.3: hover 发光脉冲 0.15→0.4)
    for (const p of parts) {
      let e = p.id === highlightId ? 0.35 : 0;
      const t0 = pulses.get(p.id);
      if (t0 !== undefined) {
        const age = t - t0;
        if (age < 1.5) e = Math.max(e, 0.15 + 0.25 * (0.5 - 0.5 * Math.cos(age * 10)) * Math.max(0, 1 - age / 1.5));
        else pulses.delete(p.id);
      }
      p.mesh.material.emissiveIntensity = e;
    }

    controls.update();
    if (flowsTick) flowsTick(t, dt, kCur);
    renderer.render(scene, camera);
  }

  // 自驱动 rAF 循环 (render 同时暴露给测试/外部步进)
  const loop = () => { render(performance.now() / 1000); requestAnimationFrame(loop); };
  requestAnimationFrame(loop);

  // resize: 跟随舞台容器
  const resize = () => {
    const el = canvas.parentElement;
    const w = el.clientWidth || 800, h = el.clientHeight || 480;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(canvas.parentElement);
  resize();

  const handle = {
    renderer, scene, camera, controls, asm, parts, hotspots,
    setExplode, setHighlight, pulsePart, render,
    get explode() { return kCur; },
    get fps() { return fps; },
    registerFlowsTick(fn) { flowsTick = fn; },
  };

  // ── Task4: 流光/粒子 (电流辉光 + 气流) — 挂 asm 随呼吸, 锚 pcb 部件随爆炸 ──
  try {
    const { createFlows } = await import("/webapp/js/flows.js");
    handle.flows = await createFlows(asm, { getPcb: () => (parts.find((p) => p.id === "pcb") || {}).mesh || null });
    flowsTick = handle.flows.tick;                // 渲染回调: render(t) 每帧驱动
  } catch (e) {
    console.warn("flows 加载失败 (流光/粒子不可用):", e);
  }

  window.__t2 = window.__t2 || {};
  window.__t2.scene = handle;                     // T7 测试调试钩
  return handle;
}
