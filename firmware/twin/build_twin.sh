#!/usr/bin/env bash
# build_twin.sh — 重建数字孪生二进制（git 忽略 *.dll/*.exe，改逻辑后跑本脚本即可）
# 依赖: gcc（MinGW，与 tests/ 主机测试同一编译器）
# 2026-09-23 起 pn_twin.dll 含 TinyML 推理器（pn_ml，DLL 导出保留）；
# 2026-10-02 泄漏检测随 spec §12 全下线：leak_detect.c/pn_ml 不再编入，
#           leak_detect.c/.h 与 ml_conformance 一并归档 deprecated/ml-leak/
set -e
cd "$(dirname "$0")"

CORE=../components/pn_core
SRC="$CORE/src/actions.c $CORE/src/closedloop.c $CORE/src/proto.c $CORE/src/cli.c ../tests/mock_hal.c"
INC="-I$CORE/include -I../tests -I."

gcc -shared -o pn_twin.dll -static-libgcc $INC twin_api.c $SRC
echo "OK pn_twin.dll (TinyML leak detection removed, spec §12)"

gcc -o twin_selftest.exe -static-libgcc $INC twin_selftest.c twin_api.c $SRC
echo "OK twin_selftest.exe"

./twin_selftest.exe
