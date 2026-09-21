#!/usr/bin/env bash
# build_twin.sh — 重建数字孪生二进制（git 忽略 *.dll/*.exe，改逻辑后跑本脚本即可）
# 依赖: gcc（MinGW，与 tests/ 主机测试同一编译器）
set -e
cd "$(dirname "$0")"

CORE=../components/pn_core
SRC="$CORE/src/actions.c $CORE/src/closedloop.c $CORE/src/proto.c $CORE/src/cli.c ../tests/mock_hal.c"
INC="-I$CORE/include -I../tests"

gcc -shared -o pn_twin.dll $INC twin_api.c $SRC
echo "✓ pn_twin.dll"

gcc -o twin_selftest.exe $INC twin_selftest.c twin_api.c $SRC
echo "✓ twin_selftest.exe"

./twin_selftest.exe
