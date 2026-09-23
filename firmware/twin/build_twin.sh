#!/usr/bin/env bash
# build_twin.sh — 重建数字孪生二进制（git 忽略 *.dll/*.exe，改逻辑后跑本脚本即可）
# 依赖: gcc（MinGW，与 tests/ 主机测试同一编译器）
# 2026-09-23 起包含 TinyML 推理器（pn_ml）+ 一致性测试（ml_conformance）
set -e
cd "$(dirname "$0")"

CORE=../components/pn_core
ML=../components/pn_ml
SRC="$CORE/src/actions.c $CORE/src/closedloop.c $CORE/src/proto.c $CORE/src/cli.c $CORE/src/leak_detect.c $ML/src/leak_infer.c $ML/src/leak_model_data.c ../tests/mock_hal.c"
INC="-I$CORE/include -I$ML/include -I../tests -I."

gcc -shared -o pn_twin.dll -static-libgcc $INC twin_api.c $SRC
echo "OK pn_twin.dll (with TinyML)"

gcc -o twin_selftest.exe -static-libgcc $INC twin_selftest.c twin_api.c $SRC
echo "OK twin_selftest.exe"

gcc -o ml_conformance.exe -static-libgcc -I$ML/include -I. ml_conformance.c $ML/src/leak_infer.c $ML/src/leak_model_data.c
./ml_conformance.exe

./twin_selftest.exe
