#!/usr/bin/env bash
# test_api.sh — 数字孪生 HTTP 接口测试（curl 驱动，目标=本机孪生服务 127.0.0.1:8000）
#
# 覆盖 /api/state /api/cmd /api/sim 三端点的协议契约与物理语义：
#   状态字位定义、阀 duty、泵 duty、充气升压率、保压微漏、释放降压、
#   抽气阀型、闭环 G(RUNNING→DONE 自动关阀)、仿真注入。
# 前置：server.py 已运行。用法：bash test_api.sh
set -u
# 测试隔离：默认在 8017 端口自起独立实例，避免与用户正在操作的 8000 服务互相干扰。
# 可用 TWIN_URL 指向已有服务（如 http://127.0.0.1:8000），或 TWIN_PYTHON 指定解释器。
TPORT="${TWIN_PORT:-8017}"
BASE="${TWIN_URL:-http://127.0.0.1:$TPORT}"
SRV_PID=""
cleanup() { [ -n "$SRV_PID" ] && kill "$SRV_PID" 2>/dev/null; }
trap cleanup EXIT
if [ -z "${TWIN_URL:-}" ]; then
  PY="${TWIN_PYTHON:-D:/MiniConda/envs/paper20-cu128/python.exe}"
  [ -x "$PY" ] || PY=python
  TWIN_PORT=$TPORT "$PY" server.py >/dev/null 2>&1 &
  SRV_PID=$!
  for _ in $(seq 1 40); do curl -s -m 1 "$BASE/api/state" >/dev/null 2>&1 && break; sleep 0.25; done
fi
pass=0; fail=0

ok() { if [ "$2" = "1" ]; then pass=$((pass+1)); echo "  ✓ $1"; else fail=$((fail+1)); echo "  ✗ $1"; fi }
jnum() { grep -o "\"$1\": *[-0-9.]*" <<<"$2" | head -1 | grep -o '[-0-9.]*$'; }
jstr() { grep -o "\"$1\": *\"[^\"]*\"" <<<"$2" | head -1 | sed 's/.*"\([^"]*\)"$/\1/'; }
sens() { grep -o '"sensors": \[[^]]*\]' <<<"$2" | grep -o '\[[^]]*\]' | tr -d '[] ' | cut -d, -f"$1"; }
numgt() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a>b)}'; }
numle() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a<=b)}'; }

state() { curl -s -m 3 "$BASE/api/state"; }
cmd()   { curl -s -m 3 -X POST "$BASE/api/cmd" -d "$1" >/dev/null; }
sim()   { curl -s -m 3 -X POST "$BASE/api/sim" -d "$1"; }
clean() { cmd 'S 31'; cmd 'X'; sleep 0.3; }

s=$(state)
# 超压等错误位是固件安全锁存（set 后不复位）。检测到锁存→POST /api/reset 虚拟断电重启自愈。
st0=$(jnum state "$s")
if [ $((st0 & 32768)) -ne 0 ] 2>/dev/null; then
  echo "  … 检测到错误锁存 (state=$st0, bit15)，/api/reset 虚拟断电重启"
  curl -s -m 3 -X POST "$BASE/api/reset" >/dev/null; sleep 0.3
  s=$(state); st0=$(jnum state "$s")
  if [ $((st0 & 32768)) -ne 0 ] 2>/dev/null; then
    echo "FATAL: 虚拟重启未能清除锁存 (state=$st0)"; exit 2
  fi
fi

echo "─ 接口：协议契约 ─"
for k in state valves pump sensors cl err; do
  ok "GET /api/state 含字段 $k" "$(grep -c "\"$k\"" <<<"$s")"
done
ok "valves 长度 7" "$(grep -c '"valves": \[[^]]*\]' <<<"$s" >/dev/null && [ "$(grep -o '[0-9]*' <<<"$(jnum n "$s")" >/dev/null; echo 1)" ] && [ "$(tr -cd ',' <<<"$(grep -o '"valves": \[[^]]*\]' <<<"$s")" | wc -c)" = "6" ] && echo 1 || echo 0)"
ok "cl 枚举合法" "$(case "$(jstr cl "$s")" in IDLE|RUNNING|DONE|TIMEOUT|ERR) echo 1;; *) echo 0;; esac)"
ok "POST /api/cmd 回 {ok:true}" "$(cmd 'T'; curl -s -m 3 -X POST "$BASE/api/cmd" -d 'T' | grep -c '"ok": *true')"

clean
echo "─ 接口：充气 I（状态字/阀 duty/物理升压） ─"
cmd 'I 7 255'; sleep 0.4
s=$(state)
ok "状态字 0x02A7=679 (泵|进气|端口1-3|传感OK)" "$([ "$(jnum state "$s")" = "679" ] && echo 1 || echo 0)"
ok "端口阀1-3 duty>0、4/5=0" "$(v=$(grep -o '"valves": \[[^]]*\]' <<<"$s" | grep -o '[0-9]*'); \
  a=($v); [ "${a[0]}" -gt 0 ] && [ "${a[1]}" -gt 0 ] && [ "${a[2]}" -gt 0 ] && [ "${a[3]}" = 0 ] && [ "${a[4]}" = 0 ] && echo 1 || echo 0)"
ok "进气阀>0、排气阀=0" "$(v=($(grep -o '"valves": \[[^]]*\]' <<<"$s" | grep -o '[0-9]*')); [ "${v[5]}" -gt 0 ] && [ "${v[6]}" = 0 ] && echo 1 || echo 0)"
ok "泵 duty=255" "$([ "$(jnum pump "$s")" = "255" ] && echo 1 || echo 0)"
p1=$(sens 1 "$s")
ok "0.4s 升压 >5 kPa (≈30kPa/s)" "$(numgt "$p1" 5 && echo 1 || echo 0)"
sleep 1.5
s=$(state); p2=$(sens 1 "$s")
ok "持续充气单调上升(>+15)" "$(awk -v a="$p2" -v b="$p1" 'BEGIN{exit !(a>b+15)}' && echo 1 || echo 0)"
v=($(grep -o '"valves": \[[^]]*\]' <<<"$s" | grep -o '[0-9]*'))
ok "阀节能：500ms 后 duty 降为保持值≤170" "$([ "${v[0]}" -gt 0 ] && [ "${v[0]}" -le 170 ] && echo 1 || echo 0)"

echo "─ 接口：保压 S（全关+微漏） ─"
cmd 'S 7'; sleep 0.3
s=$(state)
ok "状态字仅传感OK 0x0200=512" "$([ "$(jnum state "$s")" = "512" ] && echo 1 || echo 0)"
ok "全阀 duty=0、泵停" "$(v=($(grep -o '"valves": \[[^]]*\]' <<<"$s" | grep -o '[0-9]*')); \
  [ "${v[0]}" = 0 ] && [ "${v[6]}" = 0 ] && [ "$(jnum pump "$s")" = 0 ] && echo 1 || echo 0)"
ph=$(sens 1 "$s"); sleep 0.6
ph2=$(sens 1 "$(state)")
ok "密封微漏（缓降 <0.5 kPa/0.6s）" "$(awk -v a="$ph" -v b="$ph2" 'BEGIN{exit !(a>=b && a-b<0.5)}' && echo 1 || echo 0)"

echo "─ 接口：释放 R（阀型 0x247 + 降压） ─"
cmd 'R 7'; sleep 0.3
s=$(state)
ok "状态字 0x0247=583 (排气|端口1-3|传感OK)" "$([ "$(jnum state "$s")" = "583" ] && echo 1 || echo 0)"
ok "排气阀>0、进气阀=0、泵停" "$(v=($(grep -o '"valves": \[[^]]*\]' <<<"$s" | grep -o '[0-9]*')); \
  [ "${v[6]}" -gt 0 ] && [ "${v[5]}" = 0 ] && [ "$(jnum pump "$s")" = 0 ] && echo 1 || echo 0)"
pr=$(sens 1 "$(state)"); sleep 1.0
pr2=$(sens 1 "$(state)")
RT=$(awk -v a="$pr2" -v b="$pr" 'BEGIN{printf "%.2f", a/b}')
ok "被动排气指数衰减（1s 比值 ${RT}∈0.35~0.72，理论 e^-1/1.6≈0.53）" \
  "$(awk -v a="$pr2" -v b="$pr" 'BEGIN{r=a/b; exit !(r>0.35 && r<0.72)}' && echo 1 || echo 0)"

echo "─ 接口：抽气 V（阀型 0x2C7） ─"
cmd 'V 7 255'; sleep 0.3
s=$(state)
ok "状态字 0x02C7=711 (泵|排气|端口1-3)" "$([ "$(jnum state "$s")" = "711" ] && echo 1 || echo 0)"
ok "泵 duty=255 运转" "$([ "$(jnum pump "$s")" = "255" ] && echo 1 || echo 0)"

echo "─ 接口：闭环 G（RUNNING→DONE 自动关阀） ─"
clean
cmd 'R 31'; sleep 1.5          # 先排空到低压，保证 G 有足够行程可观测 RUNNING 态
cmd 'S 31'; sleep 0.2
cmd 'G 7 40 0'; sleep 0.5
ok "启动后 cl=RUNNING" "$([ "$(jstr cl "$(state)")" = "RUNNING" ] && echo 1 || echo 0)"
for i in $(seq 1 40); do s=$(state); [ "$(jstr cl "$s")" = "DONE" ] && break; sleep 0.15; done
ok "达到目标 cl=DONE" "$([ "$(jstr cl "$s")" = "DONE" ] && echo 1 || echo 0)"
pg=$(sens 1 "$s")
ok "停在目标附近 40±3 kPa（实测 $pg）" "$(awk -v a="$pg" 'BEGIN{exit !(a>37 && a<43)}' && echo 1 || echo 0)"
v=($(grep -o '"valves": \[[^]]*\]' <<<"$s" | grep -o '[0-9]*'))
ok "完成后自动关阀全停" "$([ "${v[0]}" = 0 ] && [ "${v[6]}" = 0 ] && [ "$(jnum pump "$s")" = 0 ] && echo 1 || echo 0)"

echo "─ 接口：仿真注入 /api/sim ─"
ok "注入 S1=66 回 {ok:true}" "$(sim '1 66' | grep -c '"ok": *true')"
ok "S1 读数=66.0" "$([ "$(sens 2 "$(state)")" = "66.0" ] && echo 1 || echo 0)"
sim '1 0' >/dev/null
ok "注入 S1=0 复位" "$([ "$(sens 2 "$(state)")" = "0.0" ] && echo 1 || echo 0)"
ok "非法注入体回 {ok:false}" "$(sim 'bad body' | grep -c '"ok": *false')"

echo "─ 接口：传感器量程饱和与超压保护盲区 ─"
clean
sim '0 125' >/dev/null; sleep 0.1
sv1=$(sens 1 "$(state)")
ok "注入 125 → 按量程饱和（实测 ${sv1} ∈ 99~101）" \
  "$(awk -v a="$sv1" 'BEGIN{exit !(a>99 && a<101)}' && echo 1 || echo 0)"
sim '0 -150' >/dev/null; sleep 0.1
sv2=$(sens 1 "$(state)")
ok "注入 -150 → 饱和（实测 ${sv2} ∈ -101~-99）" \
  "$(awk -v a="$sv2" 'BEGIN{exit !(a<-99 && a>-101)}' && echo 1 || echo 0)"
s=$(state)
ok "饱和不触发超压(err=0)：阈值120>量程100=固件保护盲区(已记录)" \
  "$([ "$(jnum err "$s")" = "0" ] && [ $(( $(jnum state "$s") & 32768 )) -eq 0 ] && echo 1 || echo 0)"
ok "POST /api/reset 回 {ok:true}" "$(curl -s -m 3 -X POST "$BASE/api/reset" | grep -c '"ok": *true')"

echo "─ 接口：一阶气动物理模型 ─"
# 每项测量前 /apireset 归零（clean 只关阀不清压），保证速率从同一零表压起点可比
curl -s -m 2 -X POST "$BASE/api/reset" >/dev/null; sleep 0.2
cmd 'I 7 255'; sleep 1.0; pa=$(sens 1 "$(state)")
curl -s -m 2 -X POST "$BASE/api/reset" >/dev/null; sleep 0.2
cmd 'I 7 100'; sleep 1.0; pb=$(sens 1 "$(state)")
ok "充压速率随 duty 缩放（255:${pa}kPa vs 100:${pb}kPa / 1s @零表压）" \
  "$(awk -v a="$pa" -v b="$pb" 'BEGIN{exit !(a>b*1.8)}' && echo 1 || echo 0)"
curl -s -m 2 -X POST "$BASE/api/reset" >/dev/null; sleep 0.2
cmd 'I 7 255'; sleep 8.0; cmd 'S 7'; sleep 0.2
pp=$(sens 1 "$(state)")
ok "泵压渐近死点 55~70kPa（实测 ${pp}，无 130 假上限）" \
  "$(awk -v a="$pp" 'BEGIN{exit !(a>55 && a<70)}' && echo 1 || echo 0)"
curl -s -m 2 -X POST "$BASE/api/reset" >/dev/null; sleep 0.2
cmd 'V 7 255'; sleep 1.0
pv1=$(sens 1 "$(state)")
ok "抽气产生真实负压（1s 实测 ${pv1} < -15）" \
  "$(awk -v a="$pv1" 'BEGIN{exit !(a<-15)}' && echo 1 || echo 0)"
sleep 7.0; cmd 'S 7'; sleep 0.2
pv2=$(sens 1 "$(state)")
ok "真空渐近极限 -50~-35kPa（实测 ${pv2}）" \
  "$(awk -v a="$pv2" 'BEGIN{exit !(a>-50 && a<-35)}' && echo 1 || echo 0)"
sleep 1.0
pv3=$(sens 1 "$(state)")
ok "负压密封缓慢回充（朝 0 方向：${pv3} > ${pv2}）" "$(awk -v a="$pv3" -v b="$pv2" 'BEGIN{exit !(a>b)}' && echo 1 || echo 0)"

clean
echo ""
if [ "$fail" = "0" ]; then echo "✓ 接口测试 $pass/$pass"; exit 0; else echo "✗ 接口测试 $pass/$((pass+fail))"; exit 1; fi
