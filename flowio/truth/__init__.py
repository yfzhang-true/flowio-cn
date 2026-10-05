# -*- coding: utf-8 -*-
"""flowio.truth — 真值层: devices.json 解析与校验逻辑收拢 (spec v2.1 §2)。

* predicates — schema 谓词 (T1 十五断言谓词部分迁入; TruthSource 校验复用);
* views     — pneumatic 条目视图 (ValveSpec/PumpSpec/SensorSpec/DrivePolicy)。

注意: 本包只收代码, 真值文件本体 hardware/flowio-p1/enclosure/devices.json
永不由此包改写 (读单源, 写走 tools/ingest_device_dims.py)。
"""
from flowio.truth import predicates  # noqa: F401  (模块整体可用: flowio.truth.predicates)
from flowio.truth.predicates import (  # noqa: F401
    DEVICE_REQUIRED_FIELDS, PLACEMENT_LEGAL, PNEU_ACTUATORS, PNEU_GROUPS,
    PNEU_RAIL_V, PNEU_RATED_V, bad_dims_entries, bad_placement_entries,
    connectors_missing_port, document_problems, incomplete_entries,
    missing_bom_refs, pneu_completeness_bad, pneu_domain_ok, pneu_drive_policy_bad,
    pneu_entries, pneu_envelope_bad, pneu_groups_empty, pneu_rail_variant_ok,
    pneu_refs_dup, pneu_tag, pneu_voltage_bad)
from flowio.truth.views import (  # noqa: F401
    DrivePolicy, PumpSpec, SensorSpec, ValveSpec, drive_policy, pump_spec,
    sensor_spec, valve_specs)

__all__ = [
    "predicates",
    # predicates
    "DEVICE_REQUIRED_FIELDS", "PLACEMENT_LEGAL", "PNEU_GROUPS", "PNEU_ACTUATORS",
    "PNEU_RATED_V", "PNEU_RAIL_V", "missing_bom_refs", "incomplete_entries",
    "bad_dims_entries", "connectors_missing_port", "bad_placement_entries",
    "pneu_entries", "pneu_tag", "pneu_groups_empty", "pneu_completeness_bad",
    "pneu_domain_ok", "pneu_voltage_bad", "pneu_rail_variant_ok",
    "pneu_refs_dup", "pneu_envelope_bad", "pneu_drive_policy_bad",
    "document_problems",
    # views
    "ValveSpec", "PumpSpec", "SensorSpec", "DrivePolicy",
    "valve_specs", "pump_spec", "sensor_spec", "drive_policy",
]
