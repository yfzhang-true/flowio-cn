// firmware/twin/webapp/js/connections.js — connections.json 驱动的管路/线束渲染 (D4)
// 数据: /webapp/connections_scene.json (flowio/twin/connections_render 单源生成 ——
//       connections.json 真值边 + geom3d/case_geom/pos.csv 解析的世界折线 + 逐点锚定部件)。
// 渲染 (spec 2026-10-05 §5): 气动管 = D4-A 关键弯折点折线放样 (低面数: 径向 8);
//       电气线 = D2-A 引线桩 (CatmullRom 平滑, 红/黑双芯 + 2P 白壳视觉件, 径向 6);
//       socket/ambient 边 (插接/大气) 与 mech 边无几何 (接触已由器件模型表达/仅计数)。
// 爆炸端跟随: 每折点按 anchors[i] 取锚定部件位移重建几何 (k 变化才重建, 静止零开销)
//       —— "连接边随爆炸端点跟随, 管/线拉伸可视" 的分装式教学价值。
// 点击高亮: 器件 → 其三类连接分色增强 (气动青/电气琥珀), 其余压暗;
//       highlight() 返回 {name, counts} 供 <scene-3d> 提示 chip (mech 边计入计数)。
// 线路口径 (防误读为 bug): spec/plan 线束估算 "12 引线+2 电缆" 与图谱电气边 14 条
//       (11 lead_2p 阀引线 + 1 cable_2p 泵电缆 + 2 wire 模块内电机引线) 总数一致,
//       差异只在泵侧分类: 估算把泵电缆记 2 根/电机端子线并入引线, 实装为
//       1 根 2P 电缆 + 正/负 2 根端子线 (connections.json electrical_edges 同源)。
// 回退: connections_scene.json 加载失败 → 退回 /meshes/tubes.stl 旧单件 (优雅降级)。
import * as THREE from "three";
import { STLLoader } from "../vendor/addons/STLLoader.js";

const TUBE_RADIAL = 8, WIRE_RADIAL = 6;            // 低面数预算 (spec 风险节: 12 引线+管段)
const COL = {
  tube: 0x7ec8e3,                                  // 硅胶管 (assembly.json tubes 色同源)
  lead: [0xb03030, 0x23262b],                      // 阀引线红/黑双芯 (F0520D 实物)
  cable: [0xb03030, 0x23262b],                     // 泵电缆 2 芯
  shell: 0xf2f2f0,                                 // XH2.54-2P 白壳视觉件
};
const HI = { pneumatic: 0x6ad4ff, electrical: 0xffd27a };   // 点击高亮分色 (机械边无几何)
const SHELL_DIMS = [10.0, 7.8, 6.2];               // 2P 白壳 (devices.json C7429671 dims)

// 部件 id → 图谱位号集合 (点击高亮索引; 板内部件 U1/U3 等无图谱边 → 空匹配)
const PART_QUERIES = {
  valves: ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "VS", "VV", "VF"],
  pump: ["P1"],
  pump_case: ["PMod"],
  manifold: ["Main"],
  pcb: ["S1"],
};

export async function createConnections(parent, parts, onHighlight = () => {}) {
  const group = new THREE.Group();
  parent.add(group);

  let data;
  try {
    data = await (await fetch("connections_scene.json")).json();
    if (!data || !Array.isArray(data.edges)) throw new Error("payload 形状非法");
  } catch (e) {
    console.warn("connections_scene.json 加载失败, 回退 tubes.stl 单件:", e.message);
    const buf = await (await fetch("meshes/tubes.stl")).arrayBuffer();
    const geo = new STLLoader().parse(buf);
    geo.computeVertexNormals();
    group.add(new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
      color: COL.tube, roughness: 0.25, metalness: 0, envMapIntensity: 1.0,
    })));
    return { group, rebuild() {}, highlight() { return null; }, data: null };
  }

  const meshOf = Object.fromEntries(parts.map((p) => [p.id, p.mesh]));
  const built = [];                                // {edge, meshes} (meshes[0]=主网格)
  const index = new Map();                         // query token → [edge]

  function indexEdge(e) {
    for (const ep of [e.from, e.to]) {
      const parts2 = ep.split(".");
      for (const tok of new Set([parts2[0], parts2[1] || ""])) {
        if (!index.has(tok)) index.set(tok, []);
        index.get(tok).push(e);
      }
    }
  }

  function stdMat(color, opacity) {
    const mat = new THREE.MeshStandardMaterial({
      color, roughness: 0.4, metalness: 0.05, envMapIntensity: 0.8,
      transparent: true, opacity,
      emissive: new THREE.Color(color), emissiveIntensity: 0,
    });
    mat.userData.baseColor = color;                // 高亮复位基准色
    mat.userData.baseOpacity = opacity;            // 高亮复位基准 (fit_pending 半透明保留)
    return mat;
  }

  function tubeGeo(pts, radius, radial) {
    const path = new THREE.CurvePath();
    for (let i = 0; i < pts.length - 1; i++) path.add(new THREE.LineCurve3(pts[i], pts[i + 1]));
    return new THREE.TubeGeometry(path, Math.max(8, (pts.length - 1) * 6), radius, radial, false);
  }

  function smoothGeo(pts, radius, radial) {
    // centripetal: 尖角过冲最小的 CatmullRom 变体 (桩 = 视觉柔顺, D2-A)
    return new THREE.TubeGeometry(
      new THREE.CatmullRomCurve3(pts, false, "centripetal"),
      Math.max(12, pts.length * 6), radius, radial, false);
  }

  function offsetPts(e) {                          // 折点 + 锚定部件爆炸位移
    return e.path.map((p, i) => {
      const m = meshOf[e.anchors[i]];
      return new THREE.Vector3(p[0] + (m ? m.position.x : 0),
                               p[1] + (m ? m.position.y : 0),
                               p[2] + (m ? m.position.z : 0));
    });
  }

  function pairDir(pts) {                          // 双芯法向偏移方向 (垂直桩走向)
    const d = pts[pts.length - 1].clone().sub(pts[0]).normalize();
    const n = new THREE.Vector3(1, 0, 0).cross(d);
    return n.length() < 1e-4 ? new THREE.Vector3(0, 0, 1) : n.normalize();
  }

  for (const e of data.edges) {
    const meshes = [];
    const pts = e.path ? offsetPts(e) : null;      // socket/ambient/mech 边无折线
    if (e.render === "tube") {
      const mat = stdMat(COL.tube, e.fit_pending ? 0.5 : 0.96);
      const m = new THREE.Mesh(tubeGeo(pts, e.radius, TUBE_RADIAL), mat);
      group.add(m);
      meshes.push(m);
    } else if (e.render === "wire") {
      const pair = e.kind === "lead_2p" ? COL.lead : COL.cable;
      const n = pairDir(pts).multiplyScalar(e.radius + 0.35);
      for (let k = 0; k < 2; k++) {
        const off = k === 0 ? n : n.clone().negate();
        const m = new THREE.Mesh(smoothGeo(pts.map((p) => p.clone().add(off)),
                                           e.radius, WIRE_RADIAL),
                                 stdMat(pair[k], 1.0));
        group.add(m);
        meshes.push(m);
      }
      if (e.kind === "lead_2p") {                  // 2P 白壳视觉件 (插件入插座方向)
        const dir = pts[pts.length - 1].clone().sub(pts[pts.length - 2]).normalize();
        const shell = new THREE.Mesh(new THREE.BoxGeometry(...SHELL_DIMS),
                                     stdMat(COL.shell, 0.95));
        shell.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir);
        shell.position.copy(pts[pts.length - 1]).addScaledVector(dir, -1.0);
        shell.userData.shell = true;
        group.add(shell);
        meshes.push(shell);
      }
    }
    indexEdge(e);                                  // 无几何边也入索引 (计数/高亮匹配)
    if (meshes.length) built.push({ e, meshes });
  }

  let lastK = null;

  function rebuild(k) {                            // 爆炸端跟随: k 变化才重建几何
    if (lastK !== null && Math.abs(k - lastK) < 0.002) return;
    lastK = k;
    for (const { e, meshes } of built) {
      const pts = offsetPts(e);
      const n = pairDir(pts).multiplyScalar(e.radius + 0.35);
      meshes.forEach((m, k2) => {
        if (m.userData.shell) return;              // 白壳只在段末重对向 (下方统一处理)
        let geo;
        if (e.render === "tube") geo = tubeGeo(pts, e.radius, TUBE_RADIAL);
        else {
          const off = k2 === 0 ? n : n.clone().negate();
          geo = smoothGeo(pts.map((p) => p.clone().add(off)), e.radius, WIRE_RADIAL);
        }
        m.geometry.dispose();
        m.geometry = geo;
      });
      const shell = meshes.find((m) => m.userData.shell);
      if (shell) shellPlace(shell, pts,
        pts[pts.length - 1].clone().sub(pts[pts.length - 2]).normalize());
    }
  }

  function shellPlace(shell, pts, dir) {
    shell.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir);
    shell.position.copy(pts[pts.length - 1]).addScaledVector(dir, -1.0);
  }

  function setEdgeEmphasis(e, mode) {              // mode: "pneumatic"/"electrical"/"dim"/null
    const rec = built.find((b) => b.e === e);
    if (!rec) return;
    for (const m of rec.meshes) {
      const mat = m.material;
      if (mode === null || mode === undefined) {   // 复位: 基准色/基准透明度
        mat.emissive.setHex(mat.userData.baseColor);
        mat.emissiveIntensity = 0;
        mat.opacity = mat.userData.baseOpacity;
      } else if (mode === "dim") {
        mat.emissiveIntensity = 0;
        mat.opacity = Math.min(mat.userData.baseOpacity, 0.12);
      } else {                                     // 分色增强 (气动青/电气琥珀)
        mat.emissive.setHex(HI[mode]);
        mat.emissiveIntensity = 0.55;
        mat.opacity = 1.0;
      }
    }
  }

  function highlight(query) {                      // query: 位号/部件面/部件 id 或 null
    if (query === null) {
      for (const { e } of built) setEdgeEmphasis(e, null);
      return null;
    }
    const toks = PART_QUERIES[query] || [query];
    const hitEdges = new Set();
    for (const t of toks) for (const e of index.get(t) || []) hitEdges.add(e);
    for (const { e } of built) {
      setEdgeEmphasis(e, hitEdges.has(e) ? (e.cls === "pneumatic" ? "pneumatic" : "electrical")
                                         : "dim");
    }
    // 计数 = 真值全量边 (器件查询: 该器件三类边合计, 含无几何的 socket/mech/ambient);
    //         部件面查询 (如 J10/S_wall): 按命中边分类计数 (面级接触语义)
    const counts = { pneumatic: 0, electrical: 0, mechanical: 0 };
    const devs = toks.filter((t) => data.counts[t]);
    let name = query;
    if (devs.length) {
      for (const dev of devs) {
        name = data.devices[dev] ? data.devices[dev].name : dev;
        for (const k of Object.keys(counts)) counts[k] += data.counts[dev][k] || 0;
      }
    } else {
      for (const e of hitEdges) counts[e.cls] += 1;
    }
    if (query === "valves") name = "阀阵 11 只 (V1-V8/VS/VV/VF)";
    if (query === "pump_case") name = "泵模块壳 (1h 分装)";
    if (query === "manifold") name = "歧管/主模块气动面";
    if (query === "pcb") name = devs.length ? name : "P1 主板 (板内走线不入图谱)";
    return { name, counts, hit: hitEdges.size };
  }

  return { group, rebuild, highlight, data };
}
