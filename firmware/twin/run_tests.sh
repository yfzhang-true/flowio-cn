#!/usr/bin/env bash
# run_tests.sh — 三层测试一键运行（自起 8017 隔离实例，不干扰浏览器正在用的 8000）
# 用法：bash run_tests.sh          （cd firmware/twin）
#   TWIN_PYTHON  指定 python 解释器（默认 conda paper20-cu128，回退 PATH python）
set -u
cd "$(dirname "$0")"
PY="${TWIN_PYTHON:-D:/MiniConda/envs/paper20-cu128/python.exe}"
[ -x "$PY" ] || PY=python
NODE_BIN=node
[ -n "${NODE_PATH:-}" ] || export NODE_PATH="${TWIN_NODE_PATH:-}"

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
echo; echo "═══ 1/4 静态冒烟 check.js ═══"
$NODE_BIN check.js gui.html || rc=1

echo; echo "═══ 2/4 接口测试 test_api.sh ═══"
bash test_api.sh || rc=1

echo; echo "═══ 3/4 单元测试 test_gui.js ═══"
$NODE_BIN test_gui.js || { [ $? -eq 2 ] && echo "（SKIP）" || rc=1; }

echo; echo "═══ 4/4 功能测试 test_e2e.js ═══"
$NODE_BIN test_e2e.js || rc=1

echo; echo "═══ 完成（退出码 $rc）═══"
exit $rc
