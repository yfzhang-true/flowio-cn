#!/usr/bin/env bash
# 用 ESP-IDF 构建目标机固件（通过 cmd 调 export.bat，避免 bash 环境差异）
# 用法: ./idf_build.sh [flash monitor]
set -e
IDF_DIR="E:\\Espressif\\frameworks\\esp-idf-v5.5.5"
PROJ_DIR="E:\\FLOWIO\\firmware"
ACTION="${1:-build}"
cmd //c "call $IDF_DIR\\export.bat >nul 2>&1 && cd /d $PROJ_DIR && idf.py $ACTION"
