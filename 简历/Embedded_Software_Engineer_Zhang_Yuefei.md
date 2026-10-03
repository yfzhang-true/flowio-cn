# Zhang Yuefei — Embedded Software Engineer

Shanghai, China · 13162881437 · yuefeizzz@163.com
**GitHub: github.com/yfzhang-true** (FLOWIO-CN full-stack open-source project — all claims verifiable in code)

## Summary

3 years of embedded software development: 2 years of avionics DSP firmware at a state-owned aerospace enterprise (AG600 SSPC, DO-178C airworthiness), followed by independent full-stack delivery of an ESP32-S3 open-source hardware product — from 4-layer PCB, ESP-IDF/FreeRTOS firmware, and BLE GATT to Python SDK, five-layer automated testing (200+ assertions), and SMT manufacturing files. Proficient in C and FreeRTOS with hands-on I2C/UART/PWM driver development, NimBLE BLE application, and test automation. Trained in aerospace root-cause analysis methodology. Deeply experienced in AI Agent-driven development workflow (spec → plan → subagent execution → review loop, 200+ commits).

## Technical Skills

- **Languages**: C (expert, production code on both TI DSP and ESP32), Python (SDK development and automation scripts), C++ (basic)
- **RTOS / SDK**: FreeRTOS, ESP-IDF (ESP32-S3, CMake / idf.py build chain), Code Composer Studio (TI DSP toolchain)
- **Peripherals & Protocols**: I2C (TCA9548A 8-channel mux driver), UART, PWM (8-channel proportional valve drive), WS2812 (RMT), BLE GATT (NimBLE), custom binary protocol (0xA5 frame + CRC-8)
- **Testing & Quality**: Host-side unit testing (platform-independent C), multi-layer test automation (Web / API / E2E / consistency), DO-178C, GJB5000A, root-cause fault isolation methodology
- **Hardware & Tools**: KiCad (4-layer PCB design, DRC zero-violation), Git / GitHub, oscilloscope and lab instruments, circuit analysis and board-level debugging
- **AI-Driven Development**: AI Agent workflow for full R&D lifecycle (spec → plan → subagent execution → review loop), AI coding toolchain setup
- **Languages**: English (CET-6, fluent reading of datasheets and technical docs), Mandarin (native)

## Professional Experience

### FLOWIO-CN — Open-Source Pneumatic Soft Robotics Control Platform (Independent Project) | Jul 2026 – Present

ESP32-S3 · ESP-IDF · FreeRTOS · C · NimBLE · Python · KiCad | **github.com/yfzhang-true/flowio-cn**

Full-stack open-source alternative to MIT's FlowIO for B2B rehabilitation glove applications. Solo developer covering hardware through software, fully verifiable on GitHub.

- **Firmware Architecture**: Designed a platform-independent C logic layer (pn_core) + hardware abstraction layer (HAL) on ESP-IDF + FreeRTOS; pn_core passes 33 host-side unit tests, decoupling business logic from silicon for portability and testability.
- **Peripheral Driver Development**: Implemented TCA9548A I2C 8-channel mux, WS2812 RMT, and 8-channel PWM proportional valve drivers covering I2C bus timing, RMT peripheral configuration, and real-time control.
- **BLE Application**: Built 4-service BLE GATT stack on NimBLE (Command / Telemetry / Config / DeviceInfo) with Web Bluetooth frontend for browser-based device debugging without native apps.
- **Python SDK**: Developed flowio_sdk implementing 0xA5 protocol codec with CRC-8 cross-validated against firmware test vectors bidirectionally, ensuring cross-language consistency.
- **Test Automation**: Established five-layer automated testing — 181 test cases, 200+ assertions (host unit 33 / web 44 / API 50 / E2E 43 / protocol consistency 11) — with fully automated firmware regression verification.
- **Hardware & Manufacturing**: Independently designed 4-layer PCB (90×75 mm), clearing DRC violations from 146 to zero (freerouting 3-pass + copper pour repair + custom boardgeom full-obstacle routing library); JLC standard SMT assembly of 107 components with 100% LCSC-coded BOM; FreeCAD-modeled 3D-printed enclosure.
- **Digital Twin & Documentation**: Three.js-powered web digital twin with 3D exploded view and real-time airflow/current visualization; authored 94-page LaTeX book with 31 bibliography entries, consistency-audited with 16 items cleared.
- **AI-Driven Development**: Executed entire R&D via AI Agent workflow (spec → plan → subagent execution → review loop), 200+ git commits recording the complete decision chain.

### China Aviation Industry Group Shanghai Aviation Electric Co. (State-Owned) — Embedded Software Engineer | Jul 2023 – Jun 2025

AG600 Amphibious Aircraft · Solid-State Power Controller (SSPC) | C · TMS320F28335 DSP · DO-178C

- **Firmware Development**: Developed SSPC control firmware in C on TMS320F28335 DSP using state-machine architecture for power channel switching and protection logic, running stable 100ms / 500ms dual real-time periodic tasks.
- **Data Acquisition & Bus Communication**: Implemented multi-channel ADC acquisition and SPUI bus protocol parsing for real-time current/voltage monitoring and host communication.
- **Safety Protection**: Developed overcurrent/short-circuit protection logic ensuring safe power channel cutoff under fault conditions per airworthiness safety requirements.
- **Root-Cause Analysis**: Applied aerospace "closure" methodology (accurate localization → mechanism clarity → problem reproduction → effective countermeasures → systemic prevention) to isolate intermittent faults with full DO-178C traceability documentation.

### AI R&D Toolchain (Independent Projects) | Dec 2025 – Jul 2026

Python · AI API · EDA Automation

- **RFNext**: Built 0→1 Python API-based RF EDA automation tool scripting Keysight ADS simulation and layout workflows.
- **AI Knowledge Tool** (Feb – Apr 2026): Developed AI API-powered knowledge base covering ~80% of target API scenarios.
- AI Agent workflows and automation capabilities from this period directly enabled FLOWIO-CN's full-lifecycle AI-driven development.

## Education

- **M.S.** | Beijing University of Technology (211 / Double First-Class) | 2020.09 – 2023.06 | 2 IEEE papers published
- **B.S.** | Jiangsu University of Technology | 2015.09 – 2019.06

## Additional

- **Open Source**: FLOWIO-CN dual-licensed (Code: MIT / Hardware: CERN OHL-S), GitHub: github.com/yfzhang-true
- **Target Roles**: Embedded Software Engineer (ESP32 / ESP-IDF, Prototyping & Verification, BLE Application, Test Automation)
