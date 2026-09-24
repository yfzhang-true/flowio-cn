"""serial_monitor.py — 真机双传感器实时监测（bring-up/演示工具）

用法: python serial_monitor.py [秒数，默认18]
前置: FlowIO 固件已烧录、板子插在 COM3（丝印 COM 口）。
效果: 复位后连续 P 命令轮询双传感器，柱状图实时显示；结尾报峰值。
"""
import subprocess, serial, time, sys

PORT = 'COM3'
BAUD = 115200
DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 18.0

r = subprocess.run([sys.executable, '-m', 'esptool', '--chip', 'esp32s3',
                    '-p', PORT, 'run'], capture_output=True, timeout=40)
assert b'Hard resetting' in r.stdout, 'esptool run 失败——检查 USB 线/COM 口'
s = serial.Serial(); s.port = PORT; s.baudrate = BAUD
s.timeout = 2; s.dtr = False; s.rts = False
s.open()

t0 = time.time(); buf = b''
while time.time() - t0 < 6:
    buf += s.read(8192)          # 丢弃启动横幅，等零点自校准
print('── 实时监测（Ctrl+C 停止）──')
t0 = time.time(); peak0 = peak1 = -999.0
while time.time() - t0 < DURATION:
    s.reset_input_buffer(); s.write(b'P\n'); time.sleep(0.7)
    o = s.read(4096).decode('utf-8', errors='replace')
    vals = [l.strip() for l in o.splitlines() if 'sensor' in l]
    if len(vals) < 2:
        continue
    try:
        s0 = float(vals[0].split('=')[1].split()[0])
        s1 = float(vals[1].split('=')[1].split()[0])
    except (IndexError, ValueError):
        continue
    peak0 = max(peak0, s0); peak1 = max(peak1, s1)
    bar0 = '#' * max(0, int(s0 * 2) + 10)
    bar1 = '#' * max(0, int(s1 * 2) + 10)
    print(f'  {time.time()-t0:4.1f}s | s0={s0:+7.2f} {bar0:<10} | s1={s1:+7.2f} {bar1}')
print(f'── 峰值: sensor0={peak0:+.2f} kPa, sensor1={peak1:+.2f} kPa ──')
s.close()
