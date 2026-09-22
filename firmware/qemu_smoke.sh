#!/usr/bin/env bash
# qemu_smoke.sh — QEMU esp32s3 整固件冒烟测试（2026-09-22 首跑成功）
#
# 用法: bash qemu_smoke.sh          （需先 idf.py build 成功）
# 流程: merge_bin → 16MB 填充 → QEMU 启动（Octal PSRAM 8MB）→ 延迟喂 CLI 命令 → 判定
#
# 已知坑（2026-09-22 实测）：
#  1. 启动期间（esp_task_wdt_init 前后）UART 提前收到字节会触发 QEMU 中断竞态崩溃
#     → 命令延迟 10s 再发（启动 ~2s 完成，余量充足）；仍偶发则重试（≤5 次）
#  2. QEMU 不仿真 RMT/I2C → 固件 HAL 检测 chip v0.0 优雅跳过（真机不受影响）
#  3. -m 8M + -global ssi_psram,is_octal=true 才能匹配 N16R8 的 Octal PSRAM 配置
set -u
cd "$(dirname "$0")"

QEMU="/e/Espressif/tools/qemu-xtensa/esp_develop_9.2.2_20260417/qemu/bin/qemu-system-xtensa.exe"
PY="E:/Espressif/python_env/idf5.5_py3.11_env/Scripts/python.exe"
IMG="build/flash_image.bin"

[ -x "$QEMU" ] || { echo "✗ QEMU 未安装: $QEMU"; exit 1; }
[ -f build/flowio_p0.bin ] || { echo "✗ 固件未构建，先跑 build_n16r8.ps1"; exit 1; }

echo "── 合并烧录镜像"
"$PY" -m esptool --chip esp32s3 merge_bin -o "$IMG" \
  --flash_mode dio --flash_freq 80m --flash_size 16MB \
  0x0 build/bootloader/bootloader.bin \
  0x8000 build/partition_table/partition-table.bin \
  0x10000 build/flowio_p0.bin > /dev/null 2>&1 || { echo "✗ merge_bin 失败"; exit 1; }
truncate -s 16M "$IMG"

echo "── QEMU 启动 + CLI 冒烟（F 自检 / I 充气 / S 停止）"
for i in 1 2 3 4 5; do
  (sleep 10; printf "F\n"; sleep 5; printf "I 1 255\n"; sleep 3; printf "S 1\n"; sleep 2) | \
  timeout 30 "$QEMU" -M esp32s3 -m 8M \
    -global driver=ssi_psram,property=is_octal,value=true \
    -drive file="$IMG",if=mtd,format=raw \
    -serial stdio -display none -no-reboot > build/qemu_smoke.log 2>&1
  if grep -q "P0 ready" build/qemu_smoke.log; then echo "  第 $i 次启动成功"; break; fi
  echo "  第 $i 次崩溃（TWDT 竞态），重试"
done

LOG=build/qemu_smoke.log
pass=0; fail=0
check() { if grep -q "$1" "$LOG"; then echo "  ✓ $2"; pass=$((pass+1)); else echo "  ✗ $2"; fail=$((fail+1)); fi; }
echo "── 判定"
check "P0 ready"            "固件横幅（app_main 完成）"
check "Adding pool of 8192K of PSRAM" "Octal PSRAM 8MB 初始化（sdkconfig OCTAL 验证）"
check "selftest starting"   "F 自检启动"
check "valve click test"    "阀咔哒测试执行"
check "manifold delta-P"    "汇流管 ΔP 测试执行"
check "inflate=0"           "I 1 255 命令响应"
check "stop=0"              "S 1 命令响应"

echo "── 结果: $pass 通过 / $fail 失败"
[ "$fail" -eq 0 ] && echo "✓ QEMU 冒烟全过" || exit 1
