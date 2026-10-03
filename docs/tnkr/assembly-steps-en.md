# FLOWIO-CN Assembly & Bring-Up Steps (EN)

> Derived from `firmware/BRINGUP.md` (9 chapters, 30 checkpoints).
> Each step cites its acceptance ticket (A2xx hardware / A3xx calibration).
> Precondition: JLC-assembled board (5 fab / 2 assembled), bench PSU, ST-Link
> or USB-UART adapter, and a host with ESP-IDF toolchain installed.

## Step 1 — Visual inspection & cold power-rail check (A201)

- [ ] Inspect solder joints under magnification (ICS/QFN pads, connector seating)
- [ ] Measure 3V3-to-GND resistance on the bench PSU rails before any power-up
- [ ] Verify no solder bridges on the buck converter input stage

## Step 2 — Bench supply bring-up at 3.3 V (A202)

- [ ] Current-limited supply on, expect <50 mA idle
- [ ] Scope the buck output ripple (<30 mV pk-pk) — sim reference in `tools/sim/out/`
- [ ] Confirm 5V rail only when valve supply is intentionally enabled

## Step 3 — Program ESP32-S3 via UART (A203)

- [ ] Run `build_n16r8.ps1`; flash via USB-UART
- [ ] Console shows clean boot log, correct partition table, no brownout resets

## Step 4 — I2C bus scan through TCA9548A (A204)

- [ ] Enumerate all 8 mux channels; expected device addresses per channel
- [ ] No NACK storms; pull-up levels within spec

## Step 5 — Sensor readout (A205)

- [ ] Pressure/temperature sensors report plausible values on all channels
- [ ] Cross-check one channel against a reference gauge

## Step 6 — PWM valve-drive sweep (A206)

- [ ] 8-channel duty sweep 0→100%→0; verify monotonic pressure response
- [ ] No cross-talk between channels (neighbor channels at 0%)

## Step 7 — WS2812 status LEDs (A207)

- [ ] Boot pattern, then per-channel state colors; RMT timing stable

## Step 8 — BLE GATT connect + telemetry (A208)

- [ ] Web Bluetooth console connects (Command/Telemetry/Config/DeviceInfo)
- [ ] Live telemetry stream visible in the digital twin

## Step 9 — Closed-loop pressure PID first run (A301)

- [ ] Calibrated setpoints; step response within overshoot budget
- [ ] Log session via twin `record` API for replay

## Step 10 — End-to-end glove profile via SDK + twin replay (A302)

- [ ] Run an inflation/deflation profile from `flowio_sdk`
- [ ] Replay the recorded CSV in the digital twin; curves match live run
