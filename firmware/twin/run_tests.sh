#!/usr/bin/env bash
# run_tests.sh — 三层测试一键运行（自起 8017 隔离实例，不干扰用户正在用的 8000）
# 用法：bash run_tests.sh          （cd firmware/twin）
#   TWIN_PYTHON  指定 python 解释器（默认 conda paper20-cu128，回退 PATH python）
set -u
cd "$(dirname "$0")"
PY="${TWIN_PYTHON:-D:/MiniConda/envs/paper20-cu128/python.exe}"
[ -x "$PY" ] || PY=python
NODE_BIN=node
[ -n "${NODE_PATH:-}" ] || export NODE_PATH="${TWIN_NODE_PATH:-}"

SRV_PID=""
cleanup() { [ -n "$SRV_PID" ] && kill "$SRV_PID" 2>/dev/null; }
trap cleanup EXIT

echo "═══ 启动隔离测试实例 :8017 ═══"
TWIN_PORT=8017 "$PY" server.py >/dev/null 2>&1 &
SRV_PID=$!
for _ in $(seq 1 40); do curl -s -m 1 http://127.0.0.1:8017/api/state >/dev/null 2>&1 && break; sleep 0.25; done
if ! curl -s -m 1 http://127.0.0.1:8017/api/state >/dev/null 2>&1; then
  echo "FATAL: 测试实例启动失败（检查 python/DLL：bash build_twin.sh）"; exit 2
fi
export TWIN_URL=http://127.0.0.1:8017

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
