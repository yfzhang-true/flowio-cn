# ml-leak — TinyML 泄漏检测管线归档（2026-10-02 下线）

1. 下线原因：对标 FlowIO 无此功能，2026-10-02 用户裁定整体下线（spec §12，`docs/superpowers/specs/2026-10-02-p1-board-twin-design.md`）。
2. 内容：训练/导出/评估管线（ml_*.py）、数据集（dataset/）、int8 模型（leak_model_int8.tflite）、C 一致性测试（ml_conformance.*）。
3. 仍在别处保留：`components/pn_ml` C 推理器、pn_core CLI `L` 命令、`/api/leak` 物理故障注入（开发工具）——pn_twin.dll 导出未动。
4. 复活方法：把本目录文件移回 `firmware/twin/`，恢复 server.py `/api/leakdetect` 分支 + gui.html 检测 UI + API.md §1.2b + build_twin.sh 一致性编译行。
5. 历史与训练配方见 `firmware/twin/ML-PLAN.md` / `ML-SPEC.md`（文档未删）。
