"""Standards mapping table tests: keeps the mapping table honest in CI.

The mapping table (checks/standards-mapping-v1.yaml) is a citable asset —
these tests enforce its structural contract so it cannot silently rot.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

MAPPING_PATH = (
    Path(__file__).resolve().parent.parent / "checks" / "standards-mapping-v1.yaml"
)

REQUIRED_STANDARD_KEYS = {
    "gbt36344": ["indicators"],
    "shubiaowei": ["dimensions"],
    "cqc6d": ["dimensions"],
}
REQUIRED_CHECK_KEYS = {
    "check_id",
    "name",
    "implemented",
    "gbt36344",
    "shubiaowei",
    "iso5259_2",
    "cqc6d",
}


@pytest.fixture(scope="module")
def mapping() -> dict:
    return yaml.safe_load(MAPPING_PATH.read_text(encoding="utf-8"))


def test_spec_header(mapping):
    assert mapping["spec"] == "oed-standards-mapping"
    assert mapping["version"] == "1.0"
    assert "spec_updated" in mapping


def test_standards_blocks(mapping):
    for key, required in REQUIRED_STANDARD_KEYS.items():
        block = mapping["standards"].get(key)
        assert block, f"missing standard block: {key}"
        for field in required:
            assert block.get(field), f"{key}.{field} 不能为空"


def test_check_entries_complete(mapping):
    checks = mapping["mappings"]
    assert len(checks) >= 9, "映射表应覆盖至少 9 个检查项"
    for c in checks:
        missing = REQUIRED_CHECK_KEYS - set(c)
        assert not missing, f"{c.get('check_id')}: 缺少 {missing}"
        assert c["gbt36344"], f"{c['check_id']}: 必须映射 GB/T 36344 指标"
        for ind in c["gbt36344"]:
            assert ind in mapping["standards"]["gbt36344"]["indicators"], (
                f"{c['check_id']}: 指标 '{ind}' 不在 GB/T 36344 指标表中"
            )


def test_planned_items_must_be_marked(mapping):
    """未实现的检查项必须显式 planned——不得计入已覆盖宣传。"""
    for c in mapping["mappings"]:
        if not c["implemented"]:
            assert c.get("status") == "planned" and "note" in c, (
                f"{c['check_id']}: planned 项需 status 与 note"
            )


def test_gbt36344_five_indicators_covered(mapping):
    """GB/T 36344 五大指标应全部有已实现检查项覆盖。"""
    covered = {
        ind
        for c in mapping["mappings"]
        if c["implemented"]
        for ind in c["gbt36344"]
    }
    assert set(mapping["standards"]["gbt36344"]["indicators"]) <= covered, (
        f"GB/T 36344 指标未全覆盖，缺: {set(mapping['standards']['gbt36344']['indicators']) - covered}"
    )
