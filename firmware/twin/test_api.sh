#!/usr/bin/env bash
# test_api.sh — 数字孪生 HTTP 接口测试（curl 驱动，目标=本机孪生服务 127.0.0.1:8000）
#
# 覆盖 /api/state /api/cmd /api/sim 三端点的协议契约与物理语义：
#   状态字位定义、阀 duty、泵 duty、充气升压率、保压微漏、释放降压、
#   抽气阀型、闭环 G(RUNNING→DONE 自动关阀)、仿真注入。
# 前置：server.py 已运行。用法：bash test_api.sh
set -u
BASE=http://127.0.0.1:8000
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
sleep 1.0
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
ok "被动排气降压（>15 kPa/s）" "$(awk -v a="$pr" -v b="$pr2" 'BEGIN{exit !(a-b>15)}' && echo 1 || echo 0)"

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

echo "─ 接口：超压保护锁存 + /api/reset 虚拟断电 ─"
clean
cmd 'R 31'; sleep 1.5; cmd 'S 31'; sleep 0.2
cmd 'I 7 255'; sleep 4.6; cmd 'S 7'; sleep 0.3
s=$(state)
ok "冲过 120kPa 触发超压锁存(bit15)" "$([ $(( $(jnum state "$s") & 32768 )) -ne 0 ] && echo 1 || echo 0)"
ok "err 字段=1" "$([ "$(jnum err "$s")" = "1" ] && echo 1 || echo 0)"
ok "POST /api/reset 回 {ok:true}" "$(curl -s -m 3 -X POST "$BASE/api/reset" | grep -c '"ok": *true')"
s=$(state)
ok "虚拟断电后锁存清除(err=0,bit15=0)" "$([ $(( $(jnum state "$s") & 32768 )) -eq 0 ] && [ "$(jnum err "$s")" = "0" ] && echo 1 || echo 0)"

clean
if [ "$fail" = "0" ]; then echo "✓ 接口测试 $pass/$pass"; exit 0; else echo "✗ 接口测试 $pass/$((pass+fail))"; exit 1; fi
