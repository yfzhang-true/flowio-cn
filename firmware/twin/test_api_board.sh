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
kill $SRV 2>/dev/null
