"""Quality flag vocabulary for the unified oed format.

Flags are stored per-sample in the ``quality`` column as a bitmask
(int32). Bit 0 (value 0) means "no finding". Multiple findings on the
same sample are OR-ed together.
"""
from __future__ import annotations

import enum


class QualityFlag(enum.IntFlag):
    OK = 0
    GAP = 1 << 0            # sample inside a missing-time range (imputed placeholder)
    OUTLIER = 1 << 1        # value outside plausible bounds
    ZERO_RUN = 1 << 2       # part of an abnormally long zero-power run
    UNIT_ANOMALY = 1 << 3   # channel statistics suggest wrong physical unit
    IMPOSSIBLE_VALUE = 1 << 4  # physically impossible (e.g. negative active power)
    DST_EDGE = 1 << 5       # sample lost/ambiguous at a DST transition


FLAG_NAMES = {f.name for f in QualityFlag if f.value}

# Short human-readable explanations, used by the report renderer.
FLAG_DESCRIPTIONS = {
    "GAP": "时间区间缺失（该样本为补齐占位）",
    "OUTLIER": "数值超出合理范围",
    "ZERO_RUN": "异常长的持续零功率段",
    "UNIT_ANOMALY": "统计特征疑似单位错误（如 kW 误标为 W）",
    "IMPOSSIBLE_VALUE": "物理上不可能的取值（如负的有功功率）",
    "DST_EDGE": "夏令时切换边界的模糊/丢失样本",
}
