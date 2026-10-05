#!/usr/bin/env bash
# run_tests_cli.sh — M5 cli 双跑对拍版（与 run_tests.sh 等价集；M6 转正候选，非默认）
#
# 与 run_tests.sh 的差异只有两处路由（其余段逐字等价）：
#   2c/5 L5 器件几何层  → "$PY" -m flowio test l5     （cli 分层入口：同 venv-cad
#                          同脚本同参数 "all"，输出计数行不变）
#   2e/5 新增段        → "$PY" -m flowio test quick   （cli python 侧全套：
#                          schema 15 断言 + core + twin 11 + fwgen 11 + 盲测 3）
#   其余段（check.js 静态冒烟 / L1-L3 纯 py 装配 / L4 FreeCAD 装配 /
#   test_electrical_sim 消费侧五断言 / test_api / test_gui / test_e2e）
#   与 run_tests.sh 完全一致 —— CAD 装配段委托说明：cli test 分层入口暂不覆盖
#   L1-L4（装配/干涉测试仍是脚本形态，M6+ 迁 flowio.testkit 后再路由）。
#
# 双跑对拍（M5 验收动作）：
#   bash run_tests.sh      → EXIT_A, 计数: L5 "15 PASS / 0 FAIL",
#   bash run_tests_cli.sh  → EXIT_B, 计数: L5 同上 + electrical "6 testfns"
#                            + quick 五套件；要求 EXIT_A == EXIT_B == 0 且
#                            共同段关键计数一致（见 M5 报告对拍表）。
# 切换策略（M5 裁定）：run_tests.sh 保留为默认入口，本脚本为 cli 轨道并行跑；
# M6 起连续双绿后本脚本转正为默认（run_tests.sh 降级为回退备份）—— 避免一次
# 性换轨风险。python -m flowio 需要 flowio 可导入：本脚本导出 PYTHONPATH=仓库根
# （pip install -e . 后可去掉）。
# 用法：bash run_tests_cli.sh   （cd firmware/twin）
#   TWIN_PYTHON  指定 python 解释器（默认 conda paper20-cu128，回退 PATH python）
set -u
cd "$(dirname "$0")"
PY="${TWIN_PYTHON:-D:/MiniConda/envs/paper20-cu128/python.exe}"
[ -x "$PY" ] || PY=python
NODE_BIN=node
[ -n "${NODE_PATH:-}" ] || export NODE_PATH="${TWIN_NODE_PATH:-}"

REPO="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$REPO" ] || REPO="$(cd ../.. && pwd)"
export PYTHONPATH="${REPO}${PYTHONPATH:+;$PYTHONPATH}"   # flowio 免安装可 -m

TPORT=8017
BASE="http://127.0.0.1:$TPORT"
SRV_PID=""

# 清场：Windows SO_REUSEADDR 允许多进程同绑端口 → 残留实例会截胡请求（幽灵旧状态）。
# 启动前杀掉 $TPORT 上的一切监听进程；清理用 taskkill 树杀强杀。
kill_port() {
  for pid in $(netstat -ano | grep ":$TPORT" | grep LISTENING | awk '{print $5}' | sort -u); do
    taskkill //F //T //PID "$pid" >/dev/null 2>&1
  done
  sleep 0.5
}
cleanup() {
  if [ -n "$SRV_PID" ]; then
    taskkill //F //T //PID "$SRV_PID" >/dev/null 2>&1 || kill "$SRV_PID" 2>/dev/null
  fi
}
trap cleanup EXIT

echo "═══ 启动隔离测试实例 :$TPORT ═══"
kill_port
TWIN_PORT=$TPORT "$PY" server.py >/dev/null 2>&1 &
SRV_PID=$!
for _ in $(seq 1 40); do curl -s -m 1 "$BASE/api/state" >/dev/null 2>&1 && break; sleep 0.25; done
if ! curl -s -m 1 "$BASE/api/state" >/dev/null 2>&1; then
  echo "FATAL: 测试实例启动失败（检查 python/DLL：bash build_twin.sh）"; exit 2
fi
# 物理签名验证：确认响应来自本轮新实例（新 DLL 传感器量程钳位 ±100），防双绑定幽灵。
# 注入 123 → 钳位 100，随后微漏缓降（含 curl 往返耗时），按 98~102 区间判定。
curl -s -m 2 -X POST "$BASE/api/sim" -d "0 123" >/dev/null; sleep 0.15
SV=$(curl -s -m 2 "$BASE/api/state" | grep -o '"sensors": \[[^]]*\]' | grep -o '\[[^]]*\]' | tr -d '[] ' | cut -d, -f1)
echo "$SV" | awk '{exit !($1>98 && $1<102)}' || {
  echo "FATAL: :$TPORT 上疑似残留旧实例（物理签名=$SV 不在 98~102）——请手动检查"; exit 2; }
curl -s -m 2 -X POST "$BASE/api/reset" >/dev/null
export TWIN_URL="$BASE"

rc=0
echo; echo "═══ 1/5 静态冒烟 check.js ═══"
$NODE_BIN check.js gui.html || rc=1

echo; echo "═══ 2/5 CAD 装配测试 L1/L2/L3 (纯 python; 委托说明: 暂不路由 cli) ═══"
ENC=../../hardware/flowio-p1/enclosure
"$PY" "$ENC/test_assembly.py" || rc=1

echo; echo "═══ 2b/5 CAD 干涉测试 L4 (FreeCAD; 委托说明: 暂不路由 cli) ═══"
FC_PY="E:/FreeCAD/bin/python.exe"
if [ -x "$FC_PY" ]; then
  "$FC_PY" "$ENC/test_assembly_freecad.py" || rc=1
else
  echo "（SKIP: 未找到 $FC_PY）"
fi

echo; echo "═══ 2c/5 器件几何层 L5 —— cli 路由: python -m flowio test l5 ═══"
"$PY" -m flowio test l5 || rc=1

echo; echo "═══ 2d/5 电气驱动仿真层 (消费侧五断言; 与 run_tests.sh 等价) ═══"
"$PY" test_electrical_sim.py || rc=1

echo; echo "═══ 2e/5 flowio cli python 侧全套 —— cli 路由: python -m flowio test quick ═══"
"$PY" -m flowio test quick || rc=1

echo; echo "═══ 3/5 接口测试 test_api.sh ═══"
bash test_api.sh || rc=1

echo; echo "═══ 4/5 单元测试 test_gui.js ═══"
$NODE_BIN test_gui.js || { [ $? -eq 2 ] && echo "（SKIP）" || rc=1; }

echo; echo "═══ 5/5 功能测试 test_e2e.js ═══"
$NODE_BIN test_e2e.js || rc=1

echo "═══ 完成（退出码 $rc；M5 双跑对拍: 与 run_tests.sh 退出码及共同段计数须一致）═══"
exit $rc
