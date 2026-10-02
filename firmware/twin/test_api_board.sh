#!/usr/bin/env bash
# test_api_board.sh — API v1.2 冒烟: 板级孪生/参数化仿真/时间控制/录制回放/CSV/静态资源
# 用法: cd firmware/twin && bash test_api_board.sh
set -u
KPY="E:/Program Files/KiCad/10.0/bin/python.exe"
"$KPY" server.py & SRV=$!; sleep 3
curl -s localhost:8000/api/board/state | python -c "import json,sys; d=json.load(sys.stdin); assert d['api']=='1.2' and 'rail_5v' in d and 'history' in d; print('state OK')"
curl -s -X POST localhost:8000/api/board/sim -d '{"circuit":"buck","params":{"iload":2.0}}' | python -c "import json,sys; d=json.load(sys.stdin); assert d['waves'] and d['api']=='1.2'; print('sim OK')"
curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/api/board/sim -d '{"circuit":"buck","params":{"vin":9}}' | grep -q 400 && echo "bounds OK"
curl -s -X POST localhost:8000/api/time -d '{"paused":true}' | grep -q true && echo "time OK"
curl -s localhost:8000/api/board/history/export | head -1 | grep -q t_s && echo "csv OK"
curl -s localhost:8000/api/board/assembly | python -c "import json,sys; d=json.load(sys.stdin); assert d['api']=='1.2' and len(d['parts'])==5 and 'bbox_mm' in d; print('assembly OK')"
curl -s -X POST localhost:8000/api/record -d '{"action":"start"}' >/dev/null && curl -s -X POST localhost:8000/api/cmd -d 'I 1 255' >/dev/null 2>&1; curl -s -X POST localhost:8000/api/record -d '{"action":"stop"}' | grep -q '"n"' && echo "record OK"
# presets 域表: 200 且含 bounds/default (前端动态表单依赖)
curl -s -w "\n%{http_code}" localhost:8000/api/board/sim/presets | python -c "
import json,sys
raw, code = sys.stdin.read().rsplit('\n', 1)
d = json.loads(raw); b = d['presets']['buck']
assert code == '200' and 'bounds' in b and 'default' in b and 'iload' in b['bounds'], code
print('presets OK')"
# replay 时序回放: 首次 200 (后台注入), 立即再请求 409 防重入 (事件间隔 10s→sleep 上限 0.5s, 线程必仍在跑)
c1=$(curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/api/record/replay -d '{"events":[{"t":0,"cmd":"S 1"},{"t":10,"cmd":"I 1 255"},{"t":20,"cmd":"X"}]}')
c2=$(curl -s -o /dev/null -w "%{http_code}" -m 2 -X POST localhost:8000/api/record/replay -d '{"events":[{"t":0,"cmd":"S 1"}]}')
[ "$c1" = "200" ] && [ "$c2" = "409" ] && echo "replay 200/409 OK"
# 路径穿越: /meshes/../server.py 必 404 (--path-as-is 防 curl 客户端归一化)
[ "$(curl -s --path-as-is -o /dev/null -w "%{http_code}" localhost:8000/meshes/../server.py)" = "404" ] && echo "traversal OK"
# since 截取: ?since=中位 t → history 长度 < 全量
curl -s localhost:8000/api/board/state | python -c "
import json,sys,urllib.request
d = json.load(sys.stdin); t = d['history']['t']; full = len(t)
cut = t[full // 2] if full else 0.0
d2 = json.load(urllib.request.urlopen('http://localhost:8000/api/board/state?since=%s' % cut))
n = len(d2['history']['t'])
assert 0 <= n < full, (n, full)
print('since OK (%d < %d)' % (n, full))"
kill $SRV 2>/dev/null
